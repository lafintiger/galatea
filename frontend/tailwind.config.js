/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Futuristic dark theme
        'gala': {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
          950: '#082f49',
        },
        'cyber': {
          dark: '#0a0e17',
          darker: '#060910',
          light: '#1a2332',
          accent: '#00f0ff',
          glow: '#00f0ff33',
          pink: '#ff00aa',
          purple: '#a855f7',
        }
      },
      fontFamily: {
        'display': ['Orbitron', 'sans-serif'],
        'body': ['Rajdhani', 'sans-serif'],
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'wave': 'wave 1.5s ease-in-out infinite',
        'float': 'float 3s ease-in-out infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { 
            boxShadow: '0 0 20px rgba(0, 240, 255, 0.3), 0 0 40px rgba(0, 240, 255, 0.1)' 
          },
          '50%': { 
            boxShadow: '0 0 30px rgba(0, 240, 255, 0.5), 0 0 60px rgba(0, 240, 255, 0.2)' 
          },
        },
        'wave': {
          '0%, 100%': { transform: 'scaleY(1)' },
          '50%': { transform: 'scaleY(1.5)' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
      boxShadow: {
        'cyber': '0 0 20px rgba(0, 240, 255, 0.3)',
        'cyber-lg': '0 0 40px rgba(0, 240, 255, 0.4)',
      }
    },
  },
  plugins: [],
}



