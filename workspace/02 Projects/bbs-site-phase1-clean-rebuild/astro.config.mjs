import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://bbstrats.com',
  output: 'static',
  server: {
    allowedHosts: ['nonoxidizable-chalkiest-trace.ngrok-free.dev']
  }
});
