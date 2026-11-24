import tailwindcss from '@tailwindcss/vite'
import { tanstackStart } from '@tanstack/react-start/plugin/vite'
import viteReact from '@vitejs/plugin-react'
import { nitro } from 'nitro/vite'
import { defineConfig } from 'vite'

// Local one-origin runs only: Vercel routes /api to the API service itself.
// Set API_PROXY_TARGET (for example http://127.0.0.1:8047) to forward /api to a local API.
const apiProxyTarget = process.env.API_PROXY_TARGET?.replace(/\/$/, '')

export default defineConfig({
  server: {
    host: '127.0.0.1',
    port: 3000,
    ...(apiProxyTarget ? { proxy: { '/api': { target: apiProxyTarget, changeOrigin: true } } } : {}),
  },
  resolve: {
    tsconfigPaths: true,
  },
  plugins: [
    tailwindcss(),
    tanstackStart(),
    // Produces the server output Vercel deploys; without it the site is a 404.
    nitro(apiProxyTarget ? { routeRules: { '/api/**': { proxy: `${apiProxyTarget}/api/**` } } } : {}),
    viteReact(),
  ],
})
