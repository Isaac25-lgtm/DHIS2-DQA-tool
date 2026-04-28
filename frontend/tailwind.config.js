/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          navy: "#0B1F33",
          blue: "#102A43",
          teal: "#00A6A6",
          cyan: "#37D5D6",
          surface: "#F5F7FA",
          text: "#1F2937",
          muted: "#64748B",
          border: "#D8E1EB",
          success: "#10B981",
          warning: "#F59E0B",
          danger: "#EF4444",
        },
      },
      fontFamily: {
        sans: ["Manrope", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        panel: "0 24px 60px -28px rgba(15, 23, 42, 0.28)",
        soft: "0 16px 40px -24px rgba(16, 42, 67, 0.24)",
      },
      backgroundImage: {
        "hero-grid":
          "radial-gradient(circle at top left, rgba(55, 213, 214, 0.18), transparent 38%), radial-gradient(circle at top right, rgba(0, 166, 166, 0.16), transparent 28%)",
      },
    },
  },
  plugins: [],
};

