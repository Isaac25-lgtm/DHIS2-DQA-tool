/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          navy: "#0F1E2E",
          blue: "#152638",
          teal: "#0E9070",
          cyan: "#1AAD88",
          surface: "#F0F4F7",
          text: "#0F1E2E",
          muted: "#7A92A8",
          border: "#E2EAF0",
          success: "#16A34A",
          warning: "#D97706",
          danger: "#DC2626",
        },
      },
      fontFamily: {
        sans: ["Sora", "Segoe UI", "sans-serif"],
        display: ["Playfair Display", "Georgia", "serif"],
        mono: ["DM Mono", "Cascadia Mono", "monospace"],
      },
      boxShadow: {
        panel: "0 28px 70px -34px rgba(15, 30, 46, 0.42)",
        soft: "0 2px 12px rgba(15, 30, 46, 0.07)",
      },
      backgroundImage: {
        "hero-grid":
          "radial-gradient(circle at top left, rgba(26, 173, 136, 0.15), transparent 36%), radial-gradient(circle at top right, rgba(14, 144, 112, 0.12), transparent 30%)",
      },
    },
  },
  plugins: [],
};
