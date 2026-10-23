import { env } from "cloudflare:workers";

export interface Lecture {
  id: number;
  slug: string;
  date: string;
  time_dinner: string | null;
  time_lecture: string;
  time_end: string;
  speaker_name: string;
  speaker_role: string;
  speaker_bio: string;
  speaker_linkedin: string | null;
  image_key: string | null;
  dinner_name: string | null;
  dinner_address: string | null;
  dinner_maps_url: string | null;
  lecture_name: string;
  lecture_address: string;
  lecture_maps_url: string | null;
  video_url: string | null;
  payment_url: string | null;
  signup_open: number;
}

/** Today's date in Amsterdam as YYYY-MM-DD, so a lecture stays "upcoming" for the whole evening. */
export function todayAmsterdam(): string {
  return new Intl.DateTimeFormat("sv-SE", { timeZone: "Europe/Amsterdam" }).format(new Date());
}

export async function getUpcomingLectures(): Promise<Lecture[]> {
  const { results } = await env.DB.prepare("SELECT * FROM lectures WHERE date >= ? ORDER BY date ASC")
    .bind(todayAmsterdam())
    .all<Lecture>();
  return results;
}

export async function getPastLectures(): Promise<Lecture[]> {
  const { results } = await env.DB.prepare("SELECT * FROM lectures WHERE date < ? ORDER BY date DESC")
    .bind(todayAmsterdam())
    .all<Lecture>();
  return results;
}

export async function getLectureBySlug(slug: string): Promise<Lecture | null> {
  return env.DB.prepare("SELECT * FROM lectures WHERE slug = ?").bind(slug).first<Lecture>();
}

export async function getSettings(): Promise<Record<string, string>> {
  const { results } = await env.DB.prepare("SELECT key, value FROM settings").all<{ key: string; value: string }>();
  return Object.fromEntries(results.map((r) => [r.key, r.value]));
}
