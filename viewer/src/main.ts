// Minimal MapLibre viewer (decision 0003: talks only to the Turnpoint
// REST API, never to the store/terrain/tiles modules directly).
//
// Query params: ?plan=<id> (required to show anything), ?api=<base url>
// (default http://127.0.0.1:8123), ?tiles=<source> (optional raster
// basemap served from the API's /tiles endpoint; omitted, the map shows
// just the route on a plain background — Phase 1 has no bundled chart
// data).

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

const params = new URLSearchParams(location.search);
const apiBase = params.get("api") ?? "http://127.0.0.1:8123";
const planId = params.get("plan");
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

function renderPlan(plan: Plan): void {
  const coordinates: [number, number][] = plan.turnpoints.map((tp) => [tp.lon, tp.lat]);

  if (tileSource) {
    map.addSource("basemap", {
      type: "raster",
      tiles: [`${apiBase}/tiles/${encodeURIComponent(tileSource)}/{z}/{x}/{y}.png`],
      tileSize: 256,
    });
    map.addLayer({ id: "basemap", type: "raster", source: "basemap" });
  }

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

  const bounds = coordinates.reduce(
    (b, c) => b.extend(c),
    new LngLatBounds(coordinates[0], coordinates[0]),
  );
  map.fitBounds(bounds, { padding: 60, maxZoom: 12 });
}

async function loadPlan(): Promise<void> {
  if (!planId) {
    statusEl.textContent = "No plan selected. Add ?plan=<id> to the URL.";
    return;
  }
  statusEl.textContent = `Loading plan ${planId}...`;
  try {
    const resp = await fetch(`${apiBase}/plans/${encodeURIComponent(planId)}`);
    if (!resp.ok) {
      throw new Error(`API returned ${resp.status}`);
    }
    const data = (await resp.json()) as PlanResponse;
    renderPlan(data.plan);
    statusEl.textContent = `Plan "${data.plan.name}" — ${data.legs.length} leg(s)`;
  } catch (err) {
    statusEl.textContent = `Failed to load plan: ${(err as Error).message}`;
  }
}

if (map.loaded()) {
  void loadPlan();
} else {
  map.on("load", () => void loadPlan());
}
