/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: { 950: "#0a0e14", 900: "#0d1219", 850: "#11171f", 800: "#161d27", 700: "#212a36", 600: "#2d3846" },
        line: "#243042",
        fg: { DEFAULT: "#e6edf3", dim: "#9fb0c3", faint: "#64748b" },
        brand: { DEFAULT: "#5ec8d8", deep: "#2a9db0" },
        ok: "#3fb950",
        warn: "#d29922",
        bad: "#f85149",
        muted: "#6e7681",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      boxShadow: { panel: "0 1px 0 0 rgba(255,255,255,0.03), 0 8px 24px -12px rgba(0,0,0,0.6)" },
    },
  },
  plugins: [],
};
