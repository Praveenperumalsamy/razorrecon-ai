/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: { 900: '#0F172A', 800: '#1E293B', 700: '#334155' },
        accent: { blue: '#3B82F6', emerald: '#10B981', amber: '#F59E0B', rose: '#F43F5E' },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
