import adapter from "@sveltejs/adapter-static";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

const config = {
  kit: {
    adapter: adapter(),
    paths: {
      base: '/chatbot'
    },
    prerender: {
      // Wizard renders form/anchors client-side per step, so some in-page
      // ids (e.g. #survey-form) are absent from the step-1 prerender snapshot.
      handleMissingId: 'warn'
    }
  },
  preprocess: vitePreprocess(),
};

export default config;
