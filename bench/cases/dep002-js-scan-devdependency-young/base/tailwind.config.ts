import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  plugins: [require("tailwindcss-animate")],
} satisfies Config;
