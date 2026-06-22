import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Local-only by doctrine.
// - Dev server binds to 127.0.0.1 (never 0.0.0.0).
// - The browser talks same-origin to this dev server; requests to /api are
//   proxied server-side to the Phase 2 backend at 127.0.0.1:8741.
// - This keeps the backend CORS config untouched and ensures every hop
//   stays on localhost.
const BACKEND = "http://127.0.0.1:8741";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5273,
    strictPort: true,
    proxy: {
      "/api": {
        target: BACKEND,
        changeOrigin: false,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 5273,
    strictPort: true,
  },
});
