import type { APIRoute } from "astro";
import { env } from "cloudflare:workers";
import { attendanceFor, attendeeIcs } from "../../../lib/calendar";
import { getLectureBySlug } from "../../../lib/db";

/** Calendar file for the thank-you screen: ?keuze=diner|lezing|online */
export const GET: APIRoute = async ({ params, url }) => {
  const lecture = await getLectureBySlug(params.slug ?? "");
  if (!lecture) return new Response("Niet gevonden", { status: 404 });
  const keuze = url.searchParams.get("keuze");
  const attendance = attendanceFor(lecture, keuze === "online" ? "online" : "fysiek", keuze === "diner");
  return new Response(attendeeIcs(lecture, attendance, env.SITE_URL), {
    headers: {
      "Content-Type": "text/calendar; charset=utf-8",
      "Content-Disposition": `attachment; filename="lezing-${lecture.slug}.ics"`,
    },
  });
};
