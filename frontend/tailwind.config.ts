import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./hooks/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        leaf: "#0284c7",
        mint: "#e0f2fe",
        coral: "#e11d48",
        amber: "#d97706",
        cloud: "#eaf1f8"
      },
      boxShadow: {
        soft: "0 12px 28px rgba(15, 23, 42, 0.09)"
      }
    }
  },
  plugins: []
};

export default config;
