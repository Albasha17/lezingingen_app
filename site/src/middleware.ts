import { defineMiddleware } from "astro:middleware";
import { env } from "cloudflare:workers";
import { accessEmail } from "./lib/access";
import { getAdmin } from "./lib/db";

/**
 * Guards /admin. Cloudflare Access does the email login in front of the site; here we check
 * the signed token and that the email is in the admins table. Local dev can set DEV_ADMIN_EMAIL.
 */
export const onRequest = defineMiddleware(async (context, next) => {
  if (!context.url.pathname.startsWith("/admin")) return next();

  const email = import.meta.env.DEV && env.DEV_ADMIN_EMAIL ? env.DEV_ADMIN_EMAIL.toLowerCase() : await accessEmail(context.request);
  if (!email) {
    return new Response("Niet ingelogd. Open /admin via studiegroep.eu om in te loggen.", { status: 401 });
  }
  const admin = await getAdmin(email);
  if (!admin) {
    return new Response(`${email} heeft geen toegang tot het beheer. Vraag een beheerder om je toe te voegen.`, { status: 403 });
  }
  context.locals.admin = { email: admin.email, role: admin.role };
  const response = await next();
  response.headers.set("Cache-Control", "no-store");
  return response;
});
