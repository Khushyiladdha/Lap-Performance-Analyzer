import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies the API to the FastAPI backend (Stage 5) on :8000, so the
// frontend can call same-origin paths like POST /comparison/analyze.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/comparison": "http://127.0.0.1:8001",
      "/catalog": "http://127.0.0.1:8001",
      "/import": "http://127.0.0.1:8001",
      "/health": "http://127.0.0.1:8001",
    },
  },
});
