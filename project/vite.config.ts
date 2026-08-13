import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  base: process.env.GITHUB_PAGES === 'true' ? '/1-stop-sublet-NYU/' : '/',
  plugins: [react()],
  build: {
    minify: 'esbuild',
  },
})
