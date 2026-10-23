# studiegroep.eu

The new EU Studiegroep website: Astro on Cloudflare Workers, with a D1 database in place of the Google Sheet.
The Streamlit app in the repo root keeps running until the switch-over.

## Local development

```sh
cd site
npm install
cp .dev.vars.example .dev.vars          # local secrets; mails are printed to the console
npm run db:migrate:local
npx wrangler d1 execute studiegroep --local --file seed/dev.sql   # sample lectures
npm run dev                              # http://localhost:4321, admin at /admin
npm run check                            # type check
```

Locally `/admin` treats `DEV_ADMIN_EMAIL` as signed in. Production builds ignore it.

## First deploy (one-off, in the Cloudflare account that holds studiegroep.eu)

1. `npx wrangler login`
2. Database: `npx wrangler d1 create studiegroep --jurisdiction eu`, paste the `database_id` into `wrangler.jsonc`,
   then `npm run db:migrate:remote`.
3. Photos: `npx wrangler r2 bucket create studiegroep-photos --jurisdiction eu`.
4. Email: create a Resend account, add the domain `studiegroep.eu` there and add the DNS records it shows in
   Cloudflare DNS. Then `npx wrangler secret put RESEND_API_KEY`.
5. Spam check: create a Turnstile widget for `studiegroep.eu`; put the site key in `TURNSTILE_SITE_KEY` in
   `wrangler.jsonc` and run `npx wrangler secret put TURNSTILE_SECRET_KEY`.
6. Organiser calendar: `npx wrangler secret put CALENDAR_FEED_TOKEN` with a long random value
   (for example `openssl rand -hex 24`). The feed link then shows on /admin/instellingen.
7. Deploy: `npm run build && npx wrangler deploy`, and add `studiegroep.eu` as a custom domain on the
   `studiegroep` Worker (Workers & Pages > studiegroep > Settings > Domains).
8. Admin login: in Zero Trust > Access > Applications, add a self-hosted application for `studiegroep.eu/admin`
   with a policy "Allow, Emails ending in" anything (or "Everyone") and the One-time PIN login method. Copy the
   application's AUD tag into `ACCESS_AUD` and the team domain (`https://<team>.cloudflareaccess.com`) into
   `ACCESS_TEAM_DOMAIN` in `wrangler.jsonc`, then deploy again. Who actually gets in is decided by the
   `admins` table, which eustudiegroep@gmail.com manages at /admin/beheerders.
9. Optional: Email Routing for `info@studiegroep.eu` → eustudiegroep@gmail.com.

## Layout

- `migrations/` D1 schema: lectures, registrations, admins, settings
- `src/lib/` queries (`db.ts`), confirmation mail (`email.ts`), calendar files (`calendar.ts`),
  Access token check (`access.ts`), Turnstile (`turnstile.ts`)
- `src/middleware.ts` guards `/admin`
- `src/pages/` public pages (`/`, `/lezingen/<slug>`, `/archief`, `/afmelden/<token>`), admin pages under
  `/admin`, the organiser feed `/feed/<token>.ics` and speaker photos `/images/<key>`
