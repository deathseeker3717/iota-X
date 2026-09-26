/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        harness: {
          bg: '#0d1117',
          surface: '#161b22',
          panel: '#1f242c',
          border: '#30363d',
          accent: '#38bdf8',
          accentHover: '#0ea5e9',
          success: '#2ea043',
          error: '#f85149',
          warning: '#d29922',
          muted: '#8b949e',
        }
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'Menlo', 'Monaco', 'Consolas', '"Liberation Mono"', '"Courier New"', 'monospace'],
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
      }
    },
  },
  plugins: [],
}

