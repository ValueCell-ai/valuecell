import { defineConfig } from "orval";

export default defineConfig({
  api: {
    input: {
      target: "./openapi.json",
    },
    output: {
      client: "react-query",
      mock: true,
      target: "./generated.ts",
      schemas: "./model",
      httpClient: "fetch",
    },
  },
});
