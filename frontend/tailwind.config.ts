import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Space Grotesk", "Segoe UI", "sans-serif"],
        body: ["Space Grotesk", "Segoe UI", "sans-serif"]
      },
      colors: {
        ink: "#0c1116",
        mist: "#f5f1ec",
        clay: "#c86b3c",
        sun: "#f6c453",
        lagoon: "#2b6e6f"
      },
      boxShadow: {
        glow: "0 20px 60px rgba(0, 0, 0, 0.18)"
      },
      keyframes: {
        floatIn: {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" }
        },
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.6" }
        }
      },
      animation: {
        floatIn: "floatIn 0.6s ease-out",
        pulseSoft: "pulseSoft 1.6s ease-in-out infinite"
      }
    }
  },
  plugins: []
} satisfies Config;
