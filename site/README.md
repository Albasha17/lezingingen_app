# studiegroep.eu

The new EU Studiegroep website: Astro on Cloudflare Workers, with a D1 database in place of the Google Sheet.
The Streamlit app in the repo root keeps running until the switch-over.

## Local development

```sh
cd site
npm install
npm run db:migrate:local
npx wrangler d1 execute studiegroep --local --file seed/dev.sql   # sample lectures
npm run dev                                                        # http://localhost:4321
```

## First deploy (one-off)

1. `npx wrangler login` with the Cloudflare account that holds studiegroep.eu.
2. `npx wrangler d1 create studiegroep --jurisdiction eu` and paste the returned `database_id` into `wrangler.jsonc`.
3. `npm run db:migrate:remote`
4. `npm run build && npx wrangler deploy`
5. In the Cloudflare dashboard, add `studiegroep.eu` as a custom domain on the `studiegroep` Worker.

## Layout

- `migrations/` D1 schema (lectures, registrations, settings)
- `src/lib/db.ts` queries; `src/lib/format.ts` Dutch date and link helpers
- `src/pages/` landing page, `/lezingen/<slug>`, `/archief`
