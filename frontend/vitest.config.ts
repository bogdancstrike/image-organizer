import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": new URL("./src", import.meta.url).pathname } },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    testTimeout: 30000,
    maxWorkers: 2,
    coverage: {
      provider: "v8",
      reportOnFailure: true,
      include: ["src/**/*.{ts,tsx}"],
      reporter: ["text", "html", "json", "json-summary", "lcov"],
      thresholds: { lines: 90, statements: 90 },
    },
  },
});
