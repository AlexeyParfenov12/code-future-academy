import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({base:process.env.GITHUB_PAGES_BASE||'/',plugins:[react()],build:{chunkSizeWarningLimit:800},server:{port:5173}});
