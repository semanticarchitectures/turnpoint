// Minimal MapLibre viewer (decision 0003: talks only to the Turnpoint
// REST API, never to the store/terrain/tiles modules directly).
//
// Query params: ?plan=<id> and/or ?overlay=<id> (at least one needed to
// show anything; both may be given together), ?api=<base url> (default
// http://127.0.0.1:8123), ?tiles=<source> (optional raster basemap
// served from the API's /tiles endpoint; omitted, the map shows just
// the plan/overlay on a plain background — Phase 1 has no bundled chart
// data).

import type { Feature, FeatureCollection, Geometry } from "geojson";
import { LngLatBounds, Map as MapLibreMap, NavigationControl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

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

interface PlanResponse {
  plan: Plan;
  legs: unknown[];
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

const params = new URLSearchParams(location.search);
const apiBase = params.get("api") ?? "http://127.0.0.1:8123";
const planId = params.get("plan");
const overlayId = params.get("overlay");
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

function renderPlan(plan: Plan): [number, number][] {
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
  }

  if (lines.length > 0) {
    map.addSource("overlay-lines", { type: "geojson", data: featureCollection(lines) });
    map.addLayer({
      id: "overlay-lines",
      type: "line",
      source: "overlay-lines",
      paint: { "line-color": "#7c3aed", "line-width": 2, "line-dasharray": [2, 2] },
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
  }

  return overlay.features.flatMap((f) => f.coordinates.map(([lat, lon]) => [lon, lat] as [number, number]));
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
  if (!planId && !overlayId) {
    statusEl.textContent = "Nothing to show. Add ?plan=<id> and/or ?overlay=<id> to the URL.";
    return;
  }

  addBasemapIfRequested();

  const statusParts: string[] = [];
  const allCoordinates: [number, number][] = [];

  if (planId) {
    try {
      const data = await fetchJSON<PlanResponse>(`/plans/${encodeURIComponent(planId)}`);
      allCoordinates.push(...renderPlan(data.plan));
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

  statusEl.textContent = statusParts.join(" · ");
  fitBoundsTo(allCoordinates);
}

if (map.loaded()) {
  void loadAll();
} else {
  map.on("load", () => void loadAll());
}
