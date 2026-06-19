import { defineConfig } from "vite";

export default defineConfig({
  base: "/",
  build: {
    outDir: "dist",
    target: "es2022",
  },
  server: {
    port: 5173,
    // proxy das chamadas /api para o backend FastAPI em dev local
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
