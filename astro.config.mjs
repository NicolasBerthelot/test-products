// @ts-check
import { defineConfig } from 'astro/config';

// https://astro.build/config
export default defineConfig({
  // Remplacez par votre propre domaine si vous en configurez un plus tard.
  site: 'https://nicolasberthelot.github.io',
  // Nom du dépôt : GitHub Pages sert un projet à /<repo>/, pas à la racine.
  base: '/test-products/',
});
