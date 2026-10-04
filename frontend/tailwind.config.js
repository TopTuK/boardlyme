/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        ink: '#161616',
        paper: '#EDEDE6',
        line: '#D7D7CC',
        signal: '#E8590C',
        steel: '#6E6E66',
      },
      fontFamily: {
        sans: ['Archivo', 'system-ui', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      boxShadow: {
        offset: '4px 4px 0 0 #161616',
        'offset-sm': '3px 3px 0 0 #161616',
      },
    },
  },
  plugins: [],
}
