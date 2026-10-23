import { env } from "cloudflare:workers";
import type { Lecture, LectureInput } from "./db";
import { field, normalizeUrl, optional } from "./forms";

export function slugify(value: string): string {
  return value
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

const TIME = /^\d{2}:\d{2}$/;
const DATE = /^\d{4}-\d{2}-\d{2}$/;

/** Reads the lecture editor form. Returns the values to store, or an error message in Dutch. */
export async function parseLectureForm(form: FormData, existing: Lecture | null): Promise<{ input: LectureInput } | { error: string }> {
  const date = field(form, "date");
  const speakerName = field(form, "speaker_name");
  const timeDinner = field(form, "time_dinner");
  const timeLecture = field(form, "time_lecture");
  const timeEnd = field(form, "time_end");

  if (!DATE.test(date)) return { error: "Vul een geldige datum in." };
  if (!speakerName) return { error: "Vul de naam van de spreker in." };
  if (!TIME.test(timeLecture) || !TIME.test(timeEnd)) return { error: "Vul de starttijd en eindtijd van de lezing in." };
  if (timeDinner && !TIME.test(timeDinner)) return { error: "De starttijd van het diner klopt niet." };
  if (!field(form, "lecture_name") || !field(form, "lecture_address")) return { error: "Vul de locatie van de lezing in." };

  const online = field(form, "online") === "1";

  let imageKey = existing?.image_key ?? null;
  const photo = form.get("photo");
  if (photo instanceof File && photo.size > 0) {
    if (!photo.type.startsWith("image/")) return { error: "De foto moet een afbeelding zijn (jpg, png of webp)." };
    if (photo.size > 5 * 1024 * 1024) return { error: "De foto is groter dan 5 MB." };
    const extension = photo.type.split("/")[1]?.replace("jpeg", "jpg") ?? "img";
    imageKey = `${date}-${slugify(speakerName)}-${crypto.randomUUID().slice(0, 8)}.${extension}`;
    await env.PHOTOS.put(imageKey, photo.stream(), { httpMetadata: { contentType: photo.type } });
  } else if (field(form, "remove_photo") === "1") {
    imageKey = null;
  }

  return {
    input: {
      slug: existing?.slug ?? `${date}-${slugify(speakerName)}`,
      date,
      time_dinner: timeDinner || null,
      time_lecture: timeLecture,
      time_end: timeEnd,
      speaker_name: speakerName,
      speaker_role: field(form, "speaker_role"),
      speaker_bio: field(form, "speaker_bio").replace(/\r\n/g, "\n"),
      speaker_linkedin: normalizeUrl(optional(form, "speaker_linkedin")),
      image_key: imageKey,
      dinner_name: optional(form, "dinner_name"),
      dinner_address: optional(form, "dinner_address"),
      dinner_maps_url: normalizeUrl(optional(form, "dinner_maps_url")),
      lecture_name: field(form, "lecture_name"),
      lecture_address: field(form, "lecture_address"),
      lecture_maps_url: normalizeUrl(optional(form, "lecture_maps_url")),
      online: online ? 1 : 0,
      video_url: online ? normalizeUrl(optional(form, "video_url")) : null,
      payment_url: normalizeUrl(optional(form, "payment_url")),
      signup_open: field(form, "signup_open") === "1" ? 1 : 0,
    },
  };
}
