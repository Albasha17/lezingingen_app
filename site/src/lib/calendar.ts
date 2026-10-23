import type { Lecture, Registration } from "./db";
import { lectureTitle, mapsUrl } from "./format";

/** What one attendee goes to: start time and place depend on their choice, as in the old app. */
export interface Attendance {
  kind: "diner" | "lezing" | "online";
  summary: string; // "diner en lezing", used in sentences
  start: string; // HH:MM
  placeName: string;
  location: string;
  placeUrl: string;
}

export function attendanceFor(lecture: Lecture, status: Registration["status"], dinner: boolean): Attendance {
  if (status === "online") {
    return {
      kind: "online",
      summary: "de online lezing",
      start: lecture.time_lecture,
      placeName: "Online (videolink)",
      location: lecture.video_url ?? `${lecture.lecture_name} (online)`,
      placeUrl: lecture.video_url ?? "",
    };
  }
  if (dinner && lecture.time_dinner && lecture.dinner_name) {
    return {
      kind: "diner",
      summary: "diner en lezing",
      start: lecture.time_dinner,
      placeName: lecture.dinner_name,
      location: `${lecture.dinner_name}, ${lecture.dinner_address ?? ""}`,
      placeUrl: mapsUrl(lecture.dinner_maps_url, lecture.dinner_name, lecture.dinner_address),
    };
  }
  return {
    kind: "lezing",
    summary: "alleen de lezing",
    start: lecture.time_lecture,
    placeName: lecture.lecture_name,
    location: `${lecture.lecture_name}, ${lecture.lecture_address}`,
    placeUrl: mapsUrl(lecture.lecture_maps_url, lecture.lecture_name, lecture.lecture_address),
  };
}

export function eventTitle(lecture: Lecture): string {
  return `🇪🇺 ${lectureTitle(lecture.date)} (${lecture.speaker_name})`;
}

export function eventDescription(lecture: Lecture): string {
  const parts = [];
  if (lecture.video_url) parts.push(`Videolink: ${lecture.video_url}`);
  parts.push(`Spreker: ${lecture.speaker_name}`);
  if (lecture.speaker_bio) parts.push(lecture.speaker_bio);
  return parts.join("\n\n");
}

const compact = (date: string, time: string) => `${date.replaceAll("-", "")}T${time.replace(":", "").slice(0, 4)}00`;

export function googleCalendarUrl(lecture: Lecture, attendance: Attendance): string {
  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: eventTitle(lecture),
    dates: `${compact(lecture.date, attendance.start)}/${compact(lecture.date, lecture.time_end)}`,
    details: eventDescription(lecture),
    location: attendance.location,
    ctz: "Europe/Amsterdam",
  });
  return `https://calendar.google.com/calendar/render?${params}`;
}

// --- iCalendar ---

export interface IcsEvent {
  uid: string;
  date: string;
  start: string;
  end: string;
  summary: string;
  description: string;
  location: string;
  url?: string;
}

function escapeText(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/;/g, "\;").replace(/,/g, "\\,").replace(/\r?\n/g, "\\n");
}

/** Folds lines at 75 octets as RFC 5545 requires, without splitting multi-byte characters. */
function fold(line: string): string {
  const encoder = new TextEncoder();
  const out: string[] = [];
  let current = "";
  let size = 0;
  for (const char of line) {
    const bytes = encoder.encode(char).length;
    if (size + bytes > (out.length === 0 ? 75 : 74)) {
      out.push(current);
      current = "";
      size = 0;
    }
    current += char;
    size += bytes;
  }
  out.push(current);
  return out.join("\r\n ");
}

const VTIMEZONE_AMSTERDAM = [
  "BEGIN:VTIMEZONE",
  "TZID:Europe/Amsterdam",
  "BEGIN:DAYLIGHT",
  "TZOFFSETFROM:+0100",
  "TZOFFSETTO:+0200",
  "TZNAME:CEST",
  "DTSTART:19700329T020000",
  "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU",
  "END:DAYLIGHT",
  "BEGIN:STANDARD",
  "TZOFFSETFROM:+0200",
  "TZOFFSETTO:+0100",
  "TZNAME:CET",
  "DTSTART:19701025T030000",
  "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
  "END:STANDARD",
  "END:VTIMEZONE",
];

export function buildIcs(events: IcsEvent[], calendarName?: string): string {
  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
  const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//EU Studiegroep//studiegroep.eu//NL", "CALSCALE:GREGORIAN", "METHOD:PUBLISH"];
  if (calendarName) lines.push(`X-WR-CALNAME:${escapeText(calendarName)}`);
  lines.push(...VTIMEZONE_AMSTERDAM);
  for (const event of events) {
    lines.push(
      "BEGIN:VEVENT",
      `UID:${event.uid}`,
      `DTSTAMP:${stamp}`,
      `DTSTART;TZID=Europe/Amsterdam:${compact(event.date, event.start)}`,
      `DTEND;TZID=Europe/Amsterdam:${compact(event.date, event.end)}`,
      `SUMMARY:${escapeText(event.summary)}`,
      `DESCRIPTION:${escapeText(event.description)}`,
      `LOCATION:${escapeText(event.location)}`,
    );
    if (event.url) lines.push(`URL:${event.url}`);
    lines.push("STATUS:CONFIRMED", "END:VEVENT");
  }
  lines.push("END:VCALENDAR");
  return lines.map(fold).join("\r\n") + "\r\n";
}

/** The invite one attendee gets. The UID is stable per lecture and choice, so re-importing updates instead of duplicating. */
export function attendeeIcs(lecture: Lecture, attendance: Attendance, siteUrl: string): string {
  return buildIcs([
    {
      uid: `lezing-${lecture.id}@studiegroep.eu`,
      date: lecture.date,
      start: attendance.start,
      end: lecture.time_end,
      summary: eventTitle(lecture),
      description: eventDescription(lecture),
      location: attendance.location,
      url: `${siteUrl}/lezingen/${lecture.slug}`,
    },
  ]);
}
