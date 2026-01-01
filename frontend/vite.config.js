import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [svelte()],
    server: {
        port: 5173,
        strictPort: true,
        allowedHosts: ['obliging-fitting-cheetah.ngrok-free.app'],
        proxy: {
            '/api': {
                target: 'http://127.0.0.1:8201',
                changeOrigin: true,
            }
        }
    }
})
