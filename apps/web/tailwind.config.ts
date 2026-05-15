import type { Config } from 'tailwindcss';
export default { content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'], darkMode: 'class', theme: { extend: { colors: { brand: '#2563eb' } } }, plugins: [] } satisfies Config;
