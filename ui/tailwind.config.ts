import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          DEFAULT: "#121214",
          secondary: "#1c1e24",
          navbar: "#070708",
          hover: "#16161a",
          active: "#1B1B1C",
          red: "#f54257",
        },
        border: {
          DEFAULT: "#1c1c1c",
          focus: "#545457",
          menu: "#4E4E50",
        },
        button: {
          primary: "#0F1D2F", // 2e87e6, purple: 8e30d1
          hover: "#1a6fc9",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ["Inter"],
      },
    },
  },
  plugins: [],
};

export default config;
