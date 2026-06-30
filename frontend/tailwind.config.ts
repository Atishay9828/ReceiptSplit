import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./hooks/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#18201f",
        leaf: "#2f7d5a",
        mint: "#dff4ea",
        coral: "#e4624f",
        amber: "#f0b44c",
        cloud: "#f6f8f7"
      },
      boxShadow: {
        soft: "0 12px 28px rgba(24, 32, 31, 0.09)"
      }
    }
  },
  plugins: []
};

export default config;
