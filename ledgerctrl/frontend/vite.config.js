import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { copyFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))

// The built SPA is served by Frappe in two places:
//   /assets/ledgerctrl/command-center/  (hashed assets, cached)
//   /command_center_app                 (www page -> index.html, uncached)
// Building straight into public/ + www/ makes `npm run build` the whole deploy.
function deployToFrappe() {
  return {
    name: 'deploy-to-frappe',
    closeBundle() {
      copyFileSync(
        resolve(here, '../public/command-center/index.html'),
        resolve(here, '../www/command_center_app.html')
      )
    },
  }
}

export default defineConfig({
  base: '/assets/ledgerctrl/command-center/',
  plugins: [react(), tailwindcss(), deployToFrappe()],
  build: {
    outDir: '../public/command-center',
    emptyOutDir: true,
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://ledgerctl:8001',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
