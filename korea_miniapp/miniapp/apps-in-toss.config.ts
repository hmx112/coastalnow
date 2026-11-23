import { defineConfig } from '@apps-in-toss/web-framework/config';

// IMPORTANT: change appName to exactly match the app key in the Apps in Toss console.
// SDK 3.x: do not add the legacy brand block or duplicate native navigation in HTML.
export default defineConfig({
  appName: 'oneul-bada',
  webView: {},
  webBundleDir: 'dist',
  permissions: [],
  navigationBar: {
    withBackButton: true,
    withHomeButton: false,
    withTitle: true,
    transparentBackground: false,
    theme: 'light',
  },
});
