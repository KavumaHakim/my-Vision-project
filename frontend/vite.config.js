import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    allowedHosts: "all",
    proxy: {
      "/health":        "http://localhost:8000",
      "/video-stream":  "http://localhost:8000",
      "/face":          "http://localhost:8000",
      "/faces":         "http://localhost:8000",
      "/detections":    "http://localhost:8000",
      "/capture":       "http://localhost:8000",
      "/timeline":      "http://localhost:8000",
      "/attendance":    "http://localhost:8000",
      "/action":        "http://localhost:8000",
      "/audio":         "http://localhost:8000",
      "/pose":          "http://localhost:8000",
      "/security":      "http://localhost:8000",
    },
  },
});
