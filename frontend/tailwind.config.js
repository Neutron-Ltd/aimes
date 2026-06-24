/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      typography: ({ theme }) => ({
        invert: {
          css: {
            '--tw-prose-body': theme('colors.zinc.300'),
            '--tw-prose-headings': theme('colors.zinc.100'),
            '--tw-prose-bold': theme('colors.zinc.100'),
            '--tw-prose-links': theme('colors.sky.400'),
            '--tw-prose-code': theme('colors.emerald.300'),
            '--tw-prose-pre-code': theme('colors.zinc.300'),
            '--tw-prose-pre-bg': theme('colors.zinc.900'),
            '--tw-prose-quotes': theme('colors.zinc.400'),
            '--tw-prose-quote-borders': theme('colors.zinc.600'),
            '--tw-prose-th-borders': theme('colors.zinc.700'),
            '--tw-prose-td-borders': theme('colors.zinc.700'),
          },
        },
      }),
    },
  },
  plugins: [require('@tailwindcss/typography')],
}
