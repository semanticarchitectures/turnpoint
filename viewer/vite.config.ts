import { defineConfig } from "vite";

export default defineConfig({
  server: { port: 5173 },
  // maplibre-gl ships its own web worker bundle; Vite's esbuild-based dep
  // optimizer can mishandle worker loading for it (stale/missing
  // maplibre-gl-worker.mjs in node_modules/.vite/deps). Excluding it from
  // pre-bundling avoids that class of error.
  optimizeDeps: {
    exclude: ["maplibre-gl"],
  },
});
