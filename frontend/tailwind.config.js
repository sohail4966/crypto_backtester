/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--color-bg)',
        surface: 'var(--color-surface)',
        border: 'var(--color-border)',
        text: 'var(--color-text)',
        'text-secondary': 'var(--color-text-secondary)',
        accent: 'var(--color-accent)',
        bull: 'var(--color-bull)',
        bear: 'var(--color-bear)',
      },
    },
  },
  plugins: [],
}
