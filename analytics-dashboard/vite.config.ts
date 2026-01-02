/**
 * ACGS-2 Analytics Dashboard Vite Configuration
 *
 * Optimized for production performance with code splitting,
 * bundle optimization, and CDN-ready asset handling.
 */

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default defineConfig(({ mode }) => ({
  plugins: [
    react({
      // Enable React Fast Refresh for development
      fastRefresh: true,
    }),
  ],

  // Path resolution for cleaner imports
  resolve: {
    alias: {
      "@": resolve(__dirname, "./src"),
      "@components": resolve(__dirname, "./src/components"),
      "@layouts": resolve(__dirname, "./src/layouts"),
      "@api": resolve(__dirname, "./src/api"),
      "@utils": resolve(__dirname, "./src/utils"),
      "@types": resolve(__dirname, "./src/types"),
    },
  },

  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8080",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },

  build: {
    outDir: "dist",
    // Only enable source maps in development
    sourcemap: mode !== "production",
    // Target modern browsers for smaller bundles
    target: "esnext",
    // Chunk size warning threshold (in KB)
    chunkSizeWarningLimit: 500,
    // Minification options
    minify: "esbuild",
    // CSS code splitting
    cssCodeSplit: true,
    // Enable CSS minification
    cssMinify: true,
    // Rollup options for advanced bundling
    rollupOptions: {
      output: {
        // Manual chunk splitting for optimal caching
        manualChunks: {
          // React core - changes rarely
          "vendor-react": ["react", "react-dom"],
          // Charting library - largest dependency
          "vendor-recharts": ["recharts"],
          // Icons - used across components
          "vendor-icons": ["lucide-react"],
          // Grid layout for dashboard
          "vendor-grid": ["react-grid-layout"],
        },
        // Asset file naming with content hash for CDN caching
        assetFileNames: "assets/[ext]/[name]-[hash][extname]",
        // Chunk file naming
        chunkFileNames: "assets/js/[name]-[hash].js",
        // Entry file naming
        entryFileNames: "assets/js/[name]-[hash].js",
      },
    },
  },

  // Optimize dependencies
  optimizeDeps: {
    include: ["react", "react-dom", "recharts", "lucide-react", "react-grid-layout"],
  },

  // Enable CSS preprocessing optimizations
  css: {
    devSourcemap: true,
  },

  // Preview server configuration (for production builds)
  preview: {
    port: 5173,
    headers: {
      // CDN and caching headers for preview
      "Cache-Control": "public, max-age=31536000, immutable",
    },
  },

  // Environment variables prefix
  envPrefix: "VITE_",

  // Define build-time constants
  define: {
    __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
}));
