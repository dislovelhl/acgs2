/**
 * ACGS-2 Analytics Dashboard Tailwind Configuration
 *
 * Optimized for production with minimal CSS output.
 */

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  // Enable JIT mode for faster builds and smaller CSS
  mode: "jit",
  theme: {
    extend: {
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        shimmer: "shimmer 1.5s infinite",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
      },
      // Custom colors for analytics theming
      colors: {
        analytics: {
          50: "#eff6ff",
          100: "#dbeafe",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
        },
        insight: {
          50: "#f0fdf4",
          100: "#dcfce7",
          500: "#22c55e",
          600: "#16a34a",
        },
        anomaly: {
          50: "#fef2f2",
          100: "#fee2e2",
          500: "#ef4444",
          600: "#dc2626",
        },
        prediction: {
          50: "#faf5ff",
          100: "#f3e8ff",
          500: "#a855f7",
          600: "#9333ea",
        },
      },
    },
  },
  // Optimize for production - remove unused styles
  future: {
    hoverOnlyWhenSupported: true,
    respectDefaultRingColorOpacity: true,
  },
  plugins: [],
  // Safelist classes that might be dynamically generated
  safelist: [
    // Status colors used dynamically
    "bg-green-50",
    "bg-green-100",
    "bg-green-500",
    "bg-green-600",
    "text-green-600",
    "text-green-700",
    "text-green-800",
    "border-green-200",
    "border-green-300",
    "bg-yellow-50",
    "bg-yellow-100",
    "bg-yellow-500",
    "text-yellow-600",
    "text-yellow-700",
    "text-yellow-800",
    "border-yellow-200",
    "border-yellow-300",
    "bg-red-50",
    "bg-red-100",
    "bg-red-500",
    "text-red-600",
    "text-red-700",
    "text-red-800",
    "border-red-200",
    "border-red-300",
    "bg-orange-50",
    "bg-orange-100",
    "text-orange-600",
    "text-orange-700",
    "text-orange-800",
    "border-orange-300",
    "border-orange-500",
    "bg-blue-50",
    "bg-blue-100",
    "text-blue-600",
    "text-blue-700",
    "text-blue-800",
    "border-blue-300",
    "border-blue-500",
    "bg-purple-50",
    "text-purple-600",
    "text-purple-700",
    "bg-gray-50",
    "bg-gray-100",
    "text-gray-500",
    "text-gray-600",
    "text-gray-800",
    "border-gray-200",
    "border-gray-300",
  ],
};
