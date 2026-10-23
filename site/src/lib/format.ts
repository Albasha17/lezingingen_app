import type { Lecture } from "./db";

const MONTH_EMOJI = ["❄️", "🌨️", "🌱", "🌷", "☀️", "⛱️", "🍦", "🌾", "🍂", "🎃", "🌧️", "🎄"];

function parseDate(date: string): Date {
  // Noon UTC keeps the calendar day stable in any timezone.
  return new Date(`${date}T12:00:00Z`);
}

/** "donderdag 19 november 2026" */
export function longDate(date: string): string {
  return new Intl.DateTimeFormat("nl-NL", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(parseDate(date));
}

/** "19 november" */
export function shortDate(date: string): string {
  return new Intl.DateTimeFormat("nl-NL", { day: "numeric", month: "long", timeZone: "UTC" }).format(parseDate(date));
}

/** "Studiegroep 🌧️ November 2026", the title the current app uses. */
export function lectureTitle(date: string): string {
  const d = parseDate(date);
  const month = new Intl.DateTimeFormat("nl-NL", { month: "long", timeZone: "UTC" }).format(d);
  return `Studiegroep ${MONTH_EMOJI[d.getUTCMonth()]} ${month.charAt(0).toUpperCase()}${month.slice(1)} ${d.getUTCFullYear()}`;
}

export function mapsUrl(explicit: string | null, name: string | null, address: string | null): string {
  if (explicit && explicit.startsWith("http")) return explicit;
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${name ?? ""} ${address ?? ""}`.trim())}`;
}

export function imageUrl(lecture: Lecture): string | null {
  if (!lecture.image_key) return null;
  if (lecture.image_key.startsWith("http")) return lecture.image_key;
  return `/images/${lecture.image_key}`;
}
