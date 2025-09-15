import { reactRouter } from "@react-router/dev/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import createSvgSpritePlugin from "vite-plugin-svg-sprite";
import tsconfigPaths from "vite-tsconfig-paths";

// @ts-expect-error process is a nodejs global
const host = process.env.TAURI_DEV_HOST;

// https://vite.dev/config/
export default defineConfig(async () => ({
  plugins: [
    tailwindcss(),
    reactRouter(),
    tsconfigPaths(),
    createSvgSpritePlugin({
      exportType: "vanilla",
      include: "**/assets/svg/*.svg",
      svgo: {
        plugins: [
          {
            name: "preset-default",
            params: {
              overrides: {
                // Keep viewBox attribute, important for icon scaling
                removeViewBox: false,
                // Keep accessibility attributes
                removeUnknownsAndDefaults: {
                  keepDataAttrs: false,
                  keepAriaAttrs: true,
                },
                // Clean up IDs while maintaining uniqueness
                cleanupIds: {
                  minify: true,
                  preserve: [],
                },
                // Preserve currentColor and don't remove useful attributes
                removeUselessStrokeAndFill: false,
              },
            },
          },
          // Only remove data attributes and classes, preserve fill/stroke for currentColor
          {
            name: "removeAttrs",
            params: {
              attrs: "(data-.*|class)",
              elemSeparator: ",",
            },
          },
          // Remove unnecessary metadata and comments
          "removeMetadata",
          "removeComments",
          // Remove empty elements
          "removeEmptyText",
          "removeEmptyContainers",
          // Optimize paths and merge when possible
          "convertPathData",
          "mergePaths",
          // Convert colors but preserve currentColor
          {
            name: "convertColors",
            params: {
              currentColor: true,
            },
          },
        ],
      },
    }),
  ],

  // Vite options tailored for Tauri development and only applied in `tauri dev` or `tauri build`
  //
  // 1. prevent Vite from obscuring rust errors
  clearScreen: false,
  // 2. tauri expects a fixed port, fail if that port is not available
  server: {
    port: 1420,
    strictPort: true,
    host: host || false,
    hmr: host
      ? {
          protocol: "ws",
          host,
          port: 1421,
        }
      : undefined,
    watch: {
      // 3. tell Vite to ignore watching `src-tauri`
      ignored: ["**/src-tauri/**"],
    },
  },
}));
