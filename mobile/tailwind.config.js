/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,jsx,ts,tsx}",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        base: "#0F172A",
        "surface-1": "#1E293B",
        "surface-2": "#334155",
        "surface-3": "#475569",
        "border-subtle": "#334155",
        "border-default": "#475569",
        "text-primary": "#F1F5F9",
        "text-secondary": "#94A3B8",
        "text-tertiary": "#64748B",
        "blue-500": "#38BDF8",
        "blue-600": "#0EA5E9",
        "red-500": "#EF4444",
      },
    },
  },
  plugins: [],
};
