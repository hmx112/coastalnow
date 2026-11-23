import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import aitDevtools from '@apps-in-toss/devtools/unplugin';
import { readFile } from 'node:fs/promises';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const catalogueFile = resolve(process.cwd(), '..', 'stations.json');
const STATIONS = new Set(JSON.parse(readFileSync(catalogueFile, 'utf8')).map(item => item.slug));

// Local development ONLY: read the user's previously validated KHOA 7-day JSON.
// Never package these files into dist/. Never expose API keys to the browser.
function localKhoaData() {
  return {
    name: 'local-khoa-data-dev-only',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const url = new URL(req.url || '/', 'http://localhost');
        if (url.pathname !== '/__dev/tides') return next();
        const station = url.searchParams.get('station') || '';
        if (!STATIONS.has(station)) {
          res.statusCode = 400;
          res.end(JSON.stringify({ error: 'Invalid station' }));
          return;
        }
        try {
          const file = resolve(process.cwd(), '..', 'output', 'weekly', `${station}.json`);
          const contents = await readFile(file, 'utf8');
          res.setHeader('content-type', 'application/json; charset=utf-8');
          res.setHeader('cache-control', 'no-store');
          res.end(contents);
        } catch {
          res.statusCode = 503;
          res.setHeader('content-type', 'application/json; charset=utf-8');
          res.end(JSON.stringify({ error: 'Run run_week_check.ps1 to create local validated data' }));
        }
      });
    },
  };
}

export default defineConfig(({ command }) => ({
  plugins: [react(), aitDevtools.vite(), ...(command === 'serve' ? [localKhoaData()] : [])],
  server: { port: 3000, strictPort: true, fs: { allow: [resolve(process.cwd()), resolve(process.cwd(), '..')] } },
  build: { outDir: 'dist', sourcemap: false },
}));
