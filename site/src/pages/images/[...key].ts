import type { APIRoute } from "astro";
import { env } from "cloudflare:workers";

/** Speaker photos from the R2 bucket. Keys are unique per upload, so they can be cached for good. */
export const GET: APIRoute = async ({ params }) => {
  const object = await env.PHOTOS.get(params.key ?? "");
  if (!object) return new Response("Niet gevonden", { status: 404 });
  return new Response(object.body, {
    headers: {
      "Content-Type": object.httpMetadata?.contentType ?? "application/octet-stream",
      "Cache-Control": "public, max-age=31536000, immutable",
    },
  });
};
