// Minimal MapLibre viewer (decision 0003: talks only to the Turnpoint
// REST API, never to the store/terrain/tiles modules directly).
//
// Query params: ?plan=<id> and/or ?overlay=<id> and/or ?threats=<id,id,...>
// (at least one needed to show anything; any combination may be given
// together), ?api=<base url> (default http://127.0.0.1:8123), ?tiles=<source>
// (optional raster basemap served from the API's /tiles endpoint; omitted,
// the map shows just the plan/overlay/threats on a plain background —
// Phase 1 has no bundled chart data).

import type { Feature, FeatureCollection, Geometry } from "geojson";
import { LngLatBounds, Map as MapLibreMap, Marker, NavigationControl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import ms from "milsymbol";

interface Turnpoint {
  name: string;
  lat: number;
  lon: number;
  altitude_ft: number | null;
}

interface Plan {
  id: string;
  name: string;
  turnpoints: Turnpoint[];
}

interface Leg {
  from_name: string;
  to_name: string;
  distance_nm: number;
  true_course_deg: number;
  ete_min: number | null;
}

interface PlanResponse {
  plan: Plan;
  legs: Leg[];
}

type GeometryType = "point" | "line" | "polygon";

interface OverlayFeature {
  geometry_type: GeometryType;
  coordinates: [number, number][]; // (lat, lon) pairs -- turnpoint.core.overlay's convention
  properties: Record<string, unknown>;
}

interface Overlay {
  id: string;
  name: string;
  source_format: string;
  features: OverlayFeature[];
}

interface OverlayResponse {
  overlay: Overlay;
}

interface Threat {
  id: string;
  name: string;
  threat_type: string;
  lat: number;
  lon: number;
  engagement_radius_nm: number;
  sensor_height_ft: number;
  sidc: string | null;
}

interface ThreatResponse {
  threat: Threat;
}

const params = new URLSearchParams(location.search);
const apiBase = params.get("api") ?? "http://127.0.0.1:8123";
const planId = params.get("plan");
const overlayId = params.get("overlay");
const threatIds = (params.get("threats") ?? "").split(",").filter((id) => id.length > 0);
const tileSource = params.get("tiles");

const statusEl = document.getElementById("status") as HTMLDivElement;

const map = new MapLibreMap({
  container: "map",
  style: {
    version: 8,
    sources: {},
    layers: [
      { id: "background", type: "background", paint: { "background-color": "#e8ecef" } },
    ],
  },
  center: [0, 0],
  zoom: 2,
});

map.addControl(new NavigationControl(), "top-right");

function addBasemapIfRequested(): void {
  if (!tileSource) {
    return;
  }
  map.addSource("basemap", {
    type: "raster",
    tiles: [`${apiBase}/tiles/${encodeURIComponent(tileSource)}/{z}/{x}/{y}.png`],
    tileSize: 256,
  });
  map.addLayer({ id: "basemap", type: "raster", source: "basemap" });
}

// Text halo matches each layer's own color scheme -- readable over the
// basemap or another layer without needing a shared label background.
function textHalo(color: string): { "text-color": string; "text-halo-color": string; "text-halo-width": number } {
  return { "text-color": color, "text-halo-color": "#ffffff", "text-halo-width": 1.5 };
}

function renderPlan(plan: Plan, legs: Leg[]): [number, number][] {
  const coordinates: [number, number][] = plan.turnpoints.map((tp) => [tp.lon, tp.lat]);

  map.addSource("route-line", {
    type: "geojson",
    data: {
      type: "Feature",
      properties: {},
      geometry: { type: "LineString", coordinates },
    },
  });
  map.addLayer({
    id: "route-line",
    type: "line",
    source: "route-line",
    paint: { "line-color": "#1d4ed8", "line-width": 3 },
  });

  map.addSource("route-points", {
    type: "geojson",
    data: {
      type: "FeatureCollection",
      features: plan.turnpoints.map((tp) => ({
        type: "Feature",
        properties: { name: tp.name, altitude_ft: tp.altitude_ft },
        geometry: { type: "Point", coordinates: [tp.lon, tp.lat] },
      })),
    },
  });
  map.addLayer({
    id: "route-points",
    type: "circle",
    source: "route-points",
    paint: {
      "circle-radius": 6,
      "circle-color": "#dc2626",
      "circle-stroke-width": 2,
      "circle-stroke-color": "#ffffff",
    },
  });
  map.addLayer({
    id: "route-point-labels",
    type: "symbol",
    source: "route-points",
    layout: {
      "text-field": ["get", "name"],
      "text-size": 12,
      "text-offset": [0, 1.3],
      "text-anchor": "top",
    },
    paint: textHalo("#dc2626"),
  });

  // One label per leg, at the arithmetic midpoint between its turnpoints
  // -- a visual placement, not a geodesic one; distance_nm/true_course_deg
  // themselves come straight from the API's already-computed legs, never
  // recomputed client-side (decision 0003).
  const legLabels: Feature<Geometry>[] = legs.map((leg, i) => ({
    type: "Feature",
    properties: {
      label: `${leg.distance_nm.toFixed(1)} nm · ${Math.round(leg.true_course_deg)}°T`,
    },
    geometry: {
      type: "Point",
      coordinates: [
        (plan.turnpoints[i].lon + plan.turnpoints[i + 1].lon) / 2,
        (plan.turnpoints[i].lat + plan.turnpoints[i + 1].lat) / 2,
      ],
    },
  }));
  map.addSource("route-leg-labels", {
    type: "geojson",
    data: { type: "FeatureCollection", features: legLabels },
  });
  map.addLayer({
    id: "route-leg-labels",
    type: "symbol",
    source: "route-leg-labels",
    layout: { "text-field": ["get", "label"], "text-size": 11 },
    paint: textHalo("#1d4ed8"),
  });

  return coordinates;
}

// Overlay geometry is styled distinctly from the route (amber/violet/teal
// vs. the route's red/blue) so an imported KML/GPX/drawing never reads as
// a flight plan.
function overlayFeatureToGeoJSON(feature: OverlayFeature): Feature<Geometry> {
  const coords = feature.coordinates.map(([lat, lon]) => [lon, lat]);
  if (feature.geometry_type === "point") {
    return {
      type: "Feature",
      properties: feature.properties,
      geometry: { type: "Point", coordinates: coords[0] },
    };
  }
  if (feature.geometry_type === "line") {
    return {
      type: "Feature",
      properties: feature.properties,
      geometry: { type: "LineString", coordinates: coords },
    };
  }
  return {
    type: "Feature",
    properties: feature.properties,
    geometry: { type: "Polygon", coordinates: [coords] },
  };
}

function featureCollection(features: OverlayFeature[]): FeatureCollection {
  return { type: "FeatureCollection", features: features.map(overlayFeatureToGeoJSON) };
}

// Arithmetic mean of the ring's vertices -- a label placement, not a true
// geometric centroid; fine for a small notional polygon, not for a
// concave or very large one.
function polygonCentroid(feature: OverlayFeature): [number, number] {
  const n = feature.coordinates.length;
  const sumLat = feature.coordinates.reduce((s, [lat]) => s + lat, 0);
  const sumLon = feature.coordinates.reduce((s, [, lon]) => s + lon, 0);
  return [sumLon / n, sumLat / n];
}

// Only named features get a label -- not every source format sets `name`
// (fv-drawing features generally don't), and an empty text box is worse
// than no label.
function hasName(): ["has", string] {
  return ["has", "name"];
}

function renderOverlay(overlay: Overlay): [number, number][] {
  const points = overlay.features.filter((f) => f.geometry_type === "point");
  const lines = overlay.features.filter((f) => f.geometry_type === "line");
  const polygons = overlay.features.filter((f) => f.geometry_type === "polygon");

  if (polygons.length > 0) {
    map.addSource("overlay-polygons", { type: "geojson", data: featureCollection(polygons) });
    map.addLayer({
      id: "overlay-polygons-fill",
      type: "fill",
      source: "overlay-polygons",
      paint: { "fill-color": "#0d9488", "fill-opacity": 0.25 },
    });
    map.addLayer({
      id: "overlay-polygons-outline",
      type: "line",
      source: "overlay-polygons",
      paint: { "line-color": "#0d9488", "line-width": 2 },
    });
    map.addSource("overlay-polygon-labels", {
      type: "geojson",
      data: {
        type: "FeatureCollection",
        features: polygons.map((f) => ({
          type: "Feature",
          properties: f.properties,
          geometry: { type: "Point", coordinates: polygonCentroid(f) },
        })),
      },
    });
    map.addLayer({
      id: "overlay-polygon-labels",
      type: "symbol",
      source: "overlay-polygon-labels",
      filter: hasName(),
      layout: { "text-field": ["get", "name"], "text-size": 12 },
      paint: textHalo("#0f766e"),
    });
  }

  if (lines.length > 0) {
    map.addSource("overlay-lines", { type: "geojson", data: featureCollection(lines) });
    map.addLayer({
      id: "overlay-lines",
      type: "line",
      source: "overlay-lines",
      paint: { "line-color": "#7c3aed", "line-width": 2, "line-dasharray": [2, 2] },
    });
    map.addLayer({
      id: "overlay-line-labels",
      type: "symbol",
      source: "overlay-lines",
      filter: hasName(),
      layout: {
        "text-field": ["get", "name"],
        "text-size": 12,
        "symbol-placement": "line-center",
      },
      paint: textHalo("#6d28d9"),
    });
  }

  if (points.length > 0) {
    map.addSource("overlay-points", { type: "geojson", data: featureCollection(points) });
    map.addLayer({
      id: "overlay-points",
      type: "circle",
      source: "overlay-points",
      paint: {
        "circle-radius": 5,
        "circle-color": "#f59e0b",
        "circle-stroke-width": 2,
        "circle-stroke-color": "#ffffff",
      },
    });
    map.addLayer({
      id: "overlay-point-labels",
      type: "symbol",
      source: "overlay-points",
      filter: hasName(),
      layout: {
        "text-field": ["get", "name"],
        "text-size": 12,
        "text-offset": [0, 1.2],
        "text-anchor": "top",
      },
      paint: textHalo("#b45309"),
    });
  }

  return overlay.features.flatMap((f) => f.coordinates.map(([lat, lon]) => [lon, lat] as [number, number]));
}

const EARTH_RADIUS_M = 6371008.8; // IUGG mean radius -- a ring is a visual aid, not a plan input.
const METERS_PER_NM = 1852.0;

// Great-circle destination point, spherical approximation (decision 0003:
// this is client-side rendering math, not a call into the planning core --
// turnpoint.geodesy's ellipsoidal calculation is what actually plans a route).
function destinationPoint(lat: number, lon: number, bearingDeg: number, distanceM: number): [number, number] {
  const δ = distanceM / EARTH_RADIUS_M;
  const θ = (bearingDeg * Math.PI) / 180;
  const φ1 = (lat * Math.PI) / 180;
  const λ1 = (lon * Math.PI) / 180;
  const φ2 = Math.asin(Math.sin(φ1) * Math.cos(δ) + Math.cos(φ1) * Math.sin(δ) * Math.cos(θ));
  const λ2 =
    λ1 + Math.atan2(Math.sin(θ) * Math.sin(δ) * Math.cos(φ1), Math.cos(δ) - Math.sin(φ1) * Math.sin(φ2));
  return [(λ2 * 180) / Math.PI, (φ2 * 180) / Math.PI]; // [lon, lat]
}

function engagementRingPolygon(threat: Threat): [number, number][] {
  const distanceM = threat.engagement_radius_nm * METERS_PER_NM;
  const steps = 64;
  const ring: [number, number][] = [];
  for (let i = 0; i <= steps; i++) {
    ring.push(destinationPoint(threat.lat, threat.lon, (i * 360) / steps, distanceM));
  }
  return ring;
}

// Threats render distinctly again: a dashed red engagement ring (never
// solid -- it's a notional, caller-chosen radius, not a measured lethal
// envelope) plus a MIL-STD-2525 symbol from the threat's optional sidc
// (docs/PLAN.md Phase 3, M23), falling back to a plain marker without one.
function renderThreats(threats: Threat[]): [number, number][] {
  if (threats.length > 0) {
    map.addSource("threat-rings", {
      type: "geojson",
      data: {
        type: "FeatureCollection",
        features: threats.map((t) => ({
          type: "Feature",
          properties: { name: t.name },
          geometry: { type: "Polygon", coordinates: [engagementRingPolygon(t)] },
        })),
      },
    });
    map.addLayer({
      id: "threat-rings-fill",
      type: "fill",
      source: "threat-rings",
      paint: { "fill-color": "#dc2626", "fill-opacity": 0.08 },
    });
    map.addLayer({
      id: "threat-rings-outline",
      type: "line",
      source: "threat-rings",
      paint: { "line-color": "#991b1b", "line-width": 2, "line-dasharray": [3, 2] },
    });
  }

  for (const threat of threats) {
    const el = document.createElement("div");
    el.title = `${threat.name} (${threat.threat_type})`;
    el.style.position = "relative";
    let anchor: "center" | "top-left" = "center";
    if (threat.sidc) {
      const symbol = new ms.Symbol(threat.sidc, { size: 24 });
      const symbolAnchor = symbol.getAnchor();
      const symbolSize = symbol.getSize();
      el.style.width = `${symbolSize.width}px`;
      el.style.height = `${symbolSize.height}px`;
      const img = document.createElement("img");
      img.src = symbol.toDataURL();
      img.style.position = "absolute";
      img.style.left = `${-symbolAnchor.x}px`;
      img.style.top = `${-symbolAnchor.y}px`;
      el.appendChild(img);
      anchor = "top-left";
    } else {
      el.style.width = "14px";
      el.style.height = "14px";
      el.style.borderRadius = "50%";
      el.style.background = "#991b1b";
      el.style.border = "2px solid #ffffff";
    }

    const label = document.createElement("div");
    label.textContent = threat.name;
    label.style.position = "absolute";
    label.style.top = "100%";
    label.style.left = "50%";
    label.style.transform = "translateX(-50%)";
    label.style.marginTop = "2px";
    label.style.whiteSpace = "nowrap";
    label.style.font = "11px system-ui, sans-serif";
    label.style.color = "#991b1b";
    label.style.textShadow = "0 0 3px #fff, 0 0 3px #fff, 0 0 3px #fff, 0 0 3px #fff";
    el.appendChild(label);

    new Marker({ element: el, anchor }).setLngLat([threat.lon, threat.lat]).addTo(map);
  }

  return threats.flatMap((t) => [
    [t.lon, t.lat] as [number, number],
    ...engagementRingPolygon(t),
  ]);
}

function fitBoundsTo(allCoordinates: [number, number][]): void {
  if (allCoordinates.length === 0) {
    return;
  }
  const bounds = allCoordinates.reduce(
    (b, c) => b.extend(c),
    new LngLatBounds(allCoordinates[0], allCoordinates[0]),
  );
  map.fitBounds(bounds, { padding: 60, maxZoom: 12 });
}

async function fetchJSON<T>(path: string): Promise<T> {
  const resp = await fetch(`${apiBase}${path}`);
  if (!resp.ok) {
    throw new Error(`API returned ${resp.status}`);
  }
  return (await resp.json()) as T;
}

async function loadAll(): Promise<void> {
  if (!planId && !overlayId && threatIds.length === 0) {
    statusEl.textContent =
      "Nothing to show. Add ?plan=<id> and/or ?overlay=<id> and/or ?threats=<id,id,...> to the URL.";
    return;
  }

  addBasemapIfRequested();

  const statusParts: string[] = [];
  const allCoordinates: [number, number][] = [];

  if (planId) {
    try {
      const data = await fetchJSON<PlanResponse>(`/plans/${encodeURIComponent(planId)}`);
      allCoordinates.push(...renderPlan(data.plan, data.legs));
      statusParts.push(`Plan "${data.plan.name}" — ${data.legs.length} leg(s)`);
    } catch (err) {
      statusParts.push(`Failed to load plan: ${(err as Error).message}`);
    }
  }

  if (overlayId) {
    try {
      const data = await fetchJSON<OverlayResponse>(`/overlays/${encodeURIComponent(overlayId)}`);
      allCoordinates.push(...renderOverlay(data.overlay));
      statusParts.push(
        `Overlay "${data.overlay.name}" (${data.overlay.source_format}) — ` +
          `${data.overlay.features.length} feature(s)`,
      );
    } catch (err) {
      statusParts.push(`Failed to load overlay: ${(err as Error).message}`);
    }
  }

  if (threatIds.length > 0) {
    const threats: Threat[] = [];
    const failures: string[] = [];
    for (const threatId of threatIds) {
      try {
        const data = await fetchJSON<ThreatResponse>(`/threats/${encodeURIComponent(threatId)}`);
        threats.push(data.threat);
      } catch (err) {
        failures.push((err as Error).message);
      }
    }
    allCoordinates.push(...renderThreats(threats));
    if (threats.length > 0) {
      statusParts.push(`${threats.length} threat(s)`);
    }
    if (failures.length > 0) {
      statusParts.push(`Failed to load ${failures.length} threat(s): ${failures.join(", ")}`);
    }
  }

  statusEl.textContent = statusParts.join(" · ");
  fitBoundsTo(allCoordinates);
}

if (map.loaded()) {
  void loadAll();
} else {
  map.on("load", () => void loadAll());
}
