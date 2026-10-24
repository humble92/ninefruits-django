// Vite build for the portal and the shared sign-in pages (porting-plan 5.1, django-vite).
// `npm run build` writes static/dist/ with manifest.json; django-vite reads it
// (settings DJANGO_VITE). `npm run dev` serves the same paths with HMR (VITE_DEV_MODE=true).
import { resolve } from 'node:path';
import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
    root: resolve(import.meta.dirname, 'frontend'),
    base: '/static/dist/',
    plugins: [tailwindcss()],
    build: {
        outDir: resolve(import.meta.dirname, 'static/dist'),
        emptyOutDir: true,
        manifest: 'manifest.json',
        rollupOptions: {
            input: {
                app: resolve(import.meta.dirname, 'frontend/js/app.js'),
            },
        },
    },
    server: {
        host: '0.0.0.0',
        port: 5173,
        strictPort: true,
        origin: 'http://localhost:5173',
        cors: { origin: /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/ },
    },
});
