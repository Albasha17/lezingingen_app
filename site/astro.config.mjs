// @ts-check
import { defineConfig } from "astro/config";
import cloudflare from "@astrojs/cloudflare";

export default defineConfig({
  site: "https://studiegroep.eu",
  output: "server",
  adapter: cloudflare({ imageService: "passthrough" }),
});
