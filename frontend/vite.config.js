import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [svelte()],
    server: {
        port: 5174,
        strictPort: true,
        allowedHosts: ['obliging-fitting-cheetah.ngrok-free.app', '192.168.1.20'],
        proxy: {
            '/api': {
                target: 'http://192.168.1.20:8090',
                changeOrigin: true,
            }
        }
    }
})
