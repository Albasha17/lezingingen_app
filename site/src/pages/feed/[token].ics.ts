import type { APIRoute } from "astro";
import { env } from "cloudflare:workers";
import { buildIcs, eventDescription, type IcsEvent } from "../../lib/calendar";
import { getAllLectures, getCountsByLecture } from "../../lib/db";

/** Subscribable calendar for organisers, replacing the old write-to-Google-Calendar sync. */
export const GET: APIRoute = async ({ params }) => {
  if (!env.CALENDAR_FEED_TOKEN || params.token !== env.CALENDAR_FEED_TOKEN) {
    return new Response("Niet gevonden", { status: 404 });
  }
  const [lectures, counts] = await Promise.all([getAllLectures(), getCountsByLecture()]);
  const events: IcsEvent[] = [];
  for (const lecture of lectures) {
    const c = counts.get(lecture.id) ?? { fysiek: 0, dinner: 0, online: 0, afgemeld: 0 };
    const tally = `Aanmeldingen: ${c.fysiek} fysiek (${c.dinner} eten mee), ${c.online} online, ${c.afgemeld} afgemeld.`;
    const adminUrl = `${env.SITE_URL}/admin/lezingen/${lecture.id}/aanmeldingen`;
    if (lecture.time_dinner && lecture.dinner_name) {
      events.push({
        uid: `diner-${lecture.id}@studiegroep.eu`,
        date: lecture.date,
        start: lecture.time_dinner,
        end: lecture.time_lecture,
        summary: `🍕 Diner: ${lecture.speaker_name} (${c.dinner})`,
        description: `Diner voorafgaand aan de lezing van ${lecture.speaker_name}.\n${tally}\n${adminUrl}`,
        location: `${lecture.dinner_name}, ${lecture.dinner_address ?? ""}`,
      });
    }
    events.push({
      uid: `lezing-${lecture.id}-organisatie@studiegroep.eu`,
      date: lecture.date,
      start: lecture.time_lecture,
      end: lecture.time_end,
      summary: `🎤 Lezing: ${lecture.speaker_name} (${c.fysiek + c.online})`,
      description: `${tally}\n${adminUrl}\n\n${eventDescription(lecture)}`,
      location: `${lecture.lecture_name}, ${lecture.lecture_address}`,
    });
  }
  return new Response(buildIcs(events, "EU Studiegroep (organisatie)"), {
    headers: { "Content-Type": "text/calendar; charset=utf-8", "Cache-Control": "no-store" },
  });
};
