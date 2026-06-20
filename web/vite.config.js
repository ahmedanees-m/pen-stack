import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The frontend talks to the FastAPI gateway. In dev, proxy /api + /chat to the gateway on :8000; in prod the
// gateway serves the built dist/ from the same origin, so relative URLs (base "") work without a proxy.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/chat": { target: "http://localhost:8000", changeOrigin: true },
      "/health": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  build: { outDir: "dist", emptyOutDir: true },
});
