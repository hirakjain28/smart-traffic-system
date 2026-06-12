/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        navy:    "#0A0F1E",
        panel:   "#111827",
        elevated:"#1E293B",
        accent:  "#38BDF8",
        sgreen:  "#22C55E",
        samber:  "#F59E0B",
        sred:    "#EF4444",
        muted:   "#94A3B8",
      },
      fontFamily: {
        mono: ["JetBrains Mono", "monospace"],
        sans: ["Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
}