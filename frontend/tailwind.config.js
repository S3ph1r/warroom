/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{svelte,js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                // Dynamic Semantic Colors mapped to CSS vars
                skin: {
                    base: 'var(--bg-main)',
                    card: 'var(--bg-card)',
                    sidebar: 'var(--bg-sidebar)',
                    border: 'var(--border-main)',
                    text: 'var(--text-main)',
                    muted: 'var(--text-muted)',
                    accent: 'var(--accent-primary)',
                    secondary: 'var(--accent-secondary)',
                    pos: 'var(--positive)',
                    neg: 'var(--negative)',
                }
            },
            fontFamily: {
                'sans': ['Inter', 'sans-serif'],
                'mono': ['"JetBrains Mono"', 'monospace'],
                'space': ['"Space Grotesk"', 'sans-serif'], // Keep for cyberpunk
            }
        },
    },
    plugins: [],
}
