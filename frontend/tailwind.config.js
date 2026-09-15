/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        matrix: {
          bg: "#04070a",
          panel: "#0a1410",
          panel2: "#0d1a14",
          border: "#1d4d33",
          green: "#00ff9c",
          green2: "#00c97b",
          dim: "#5f8f76",
          red: "#ff4d6d",
          amber: "#ffc857",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Consolas", "Menlo", "monospace"],
      },
      boxShadow: {
        neon: "0 0 12px rgba(0,255,156,0.25), inset 0 0 24px rgba(0,255,156,0.04)",
      },
      animation: {
        flicker: "flicker 4s infinite",
      },
      keyframes: {
        flicker: {
          "0%,100%": { opacity: "1" },
          "48%": { opacity: "0.85" },
          "50%": { opacity: "0.6" },
          "52%": { opacity: "0.9" },
        },
      },
    },
  },
  plugins: [],
};
