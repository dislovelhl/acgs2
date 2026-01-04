/**
 * ACGS-2 Policy Marketplace Vite Configuration
 * Constitutional Hash: 018-policy-marketplace
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
      "@hooks": resolve(__dirname, "./src/hooks"),
      "@utils": resolve(__dirname, "./src/utils"),
      "@types": resolve(__dirname, "./src/types"),
      "@services": resolve(__dirname, "./src/services"),
    },
  },

  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8003",
        changeOrigin: true,
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
          // Router - used across the app
          "vendor-router": ["react-router-dom"],
          // Icons - used across components
          "vendor-icons": ["lucide-react"],
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
    include: ["react", "react-dom", "react-router-dom", "lucide-react"],
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
    __CONSTITUTIONAL_HASH__: JSON.stringify("018-policy-marketplace"),
    __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
}));
