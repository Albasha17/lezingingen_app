/// <reference types="@astrojs/cloudflare/types" />

// Bindings and vars come from worker-configuration.d.ts (`npx wrangler types --strict-vars=false`).
// Secrets are set with `wrangler secret put` and are not in wrangler.jsonc, so they are declared here.
declare namespace Cloudflare {
  interface Env {
    RESEND_API_KEY?: string;
    TURNSTILE_SECRET_KEY?: string;
    CALENDAR_FEED_TOKEN?: string;
    DEV_ADMIN_EMAIL?: string;
  }
}

declare namespace App {
  interface Locals {
    admin?: { email: string; role: "owner" | "admin" };
  }
}
