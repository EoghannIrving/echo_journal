module.exports = {
  darkMode: 'class',
  content: [
    './templates/**/*.html',
    './main.py',
  ],
  theme: {
    extend: {},
  },
  plugins: [require('@tailwindcss/typography')],
};
