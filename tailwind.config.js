/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        sky: {
          950: '#071521',
          900: '#0c2234',
          800: '#143652',
          700: '#1c4e74',
          600: '#256a9d',
        },
        card: {
          bg: '#0c2234',
          border: '#1a4163',
          hover: '#143652',
        },
        status: {
          normal: '#10b981',
          weather: '#38bdf8',
          fault: '#ef4444',
          gap: '#f59e0b',
          offline: '#6b7280',
        }
      },
    },
  },
  plugins: [],
};
