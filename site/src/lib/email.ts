import { env } from "cloudflare:workers";
import { attendanceFor, attendeeIcs, googleCalendarUrl } from "./calendar";
import type { Lecture, Registration } from "./db";
import { lectureTitle, longDate, mapsUrl, shortDate } from "./format";
import { esc } from "./html";

interface Attachment {
  filename: string;
  content: string;
  contentType: string;
}

interface Mail {
  to: string;
  subject: string;
  html: string;
  text: string;
  attachments?: Attachment[];
}

/** Sends through Resend. Without an API key (local development) the mail is printed instead. */
export async function sendMail(mail: Mail): Promise<boolean> {
  if (!env.RESEND_API_KEY) {
    console.log(`[mail] to=${mail.to} subject=${mail.subject}\n${mail.text}`);
    return true;
  }
  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      from: env.MAIL_FROM,
      reply_to: env.MAIL_REPLY_TO,
      to: [mail.to],
      subject: mail.subject,
      html: mail.html,
      text: mail.text,
      attachments: mail.attachments?.map((a) => ({
        filename: a.filename,
        content: btoa(String.fromCharCode(...new TextEncoder().encode(a.content))),
        content_type: a.contentType,
      })),
    }),
  });
  if (!response.ok) {
    console.error(`[mail] Resend error ${response.status}: ${await response.text()}`);
  }
  return response.ok;
}

const button = (href: string, label: string, color = "#4285F4") =>
  `<a href="${esc(href)}" style="background-color:${color};color:#ffffff;padding:10px 15px;text-decoration:none;border-radius:5px;font-weight:bold;display:inline-block;">${label}</a>`;

const programBlock = (color: string, title: string, time: string, place: string) =>
  `<div style="margin-bottom:15px;border:1px solid #eee;border-left:4px solid ${color};padding:15px;border-radius:4px;">
    <p style="margin:0 0 5px 0;font-weight:bold;font-size:1.1em;">${title}</p>
    <p style="margin:0 0 5px 0;"><strong>${time}</strong> (aanvang)</p>
    <p style="margin:0;">📍 ${place}</p>
  </div>`;

/** The confirmation mail, with the same content as the Streamlit app sent, plus a cancel link. */
export async function sendConfirmation(lecture: Lecture, registration: Registration): Promise<boolean> {
  if (!registration.email) return false;
  const siteUrl = env.SITE_URL;
  const attendance = attendanceFor(lecture, registration.status, Boolean(registration.dinner));
  const cancelUrl = `${siteUrl}/afmelden/${registration.cancel_token}`;
  const lectureUrl = `${siteUrl}/lezingen/${lecture.slug}`;
  const choice =
    attendance.kind === "online"
      ? "Online aanwezig (via videolink)"
      : attendance.kind === "diner"
        ? "Fysiek aanwezig mét diner"
        : "Fysiek aanwezig (alleen lezing)";

  let program = "";
  if (attendance.kind === "online") {
    program += programBlock(
      "#4285F4",
      "🎤 Lezing (online)",
      `🕢 ${lecture.time_lecture}`,
      lecture.video_url ? `<strong>Videolink</strong> · <a href="${esc(lecture.video_url)}">Open link</a>` : "<strong>Videolink volgt</strong>",
    );
  } else {
    if (attendance.kind === "diner") {
      program += programBlock(
        "#ff9800",
        "🍕 Diner",
        `🕕 ${lecture.time_dinner}`,
        `<strong>${esc(lecture.dinner_name)}</strong> (${esc(lecture.dinner_address)} · <a href="${esc(mapsUrl(lecture.dinner_maps_url, lecture.dinner_name, lecture.dinner_address))}">Route</a>)`,
      );
    }
    program += programBlock(
      "#4caf50",
      "🎤 Lezing",
      `🕢 ${lecture.time_lecture}`,
      `<strong>${esc(lecture.lecture_name)}</strong> (${esc(lecture.lecture_address)} · <a href="${esc(mapsUrl(lecture.lecture_maps_url, lecture.lecture_name, lecture.lecture_address))}">Route</a>)`,
    );
  }

  const videoBlock = lecture.video_url
    ? `<div style="margin-top:20px;padding:10px;background-color:#e8f0fe;border-radius:4px;border-left:4px solid #1a73e8;">
        <p style="margin:0;font-weight:bold;color:#1a73e8;">📹 Videolink</p>
        <p style="margin:5px 0 0 0;font-size:0.9em;">Mocht je (alsnog) online willen aansluiten, gebruik dan deze link:</p>
        <p style="margin:5px 0 0 0;"><a href="${esc(lecture.video_url)}" style="color:#1a73e8;">${esc(lecture.video_url)}</a></p>
      </div>`
    : "";

  const paymentBlock = lecture.payment_url
    ? `<p>Vergeet niet je bijdrage te betalen: <a href="${esc(lecture.payment_url)}">betaalverzoek openen</a>.</p>`
    : "";

  const html = `<html><body style="font-family:Arial,sans-serif;line-height:1.5;color:#333;">
    <p>Beste ${esc(registration.first_name)},</p>
    <p>Leuk dat je erbij bent op <strong>${esc(longDate(lecture.date))}</strong>! 👋 Hier zijn je details:</p>
    <div style="background-color:#f9f9f9;padding:15px;border-radius:5px;border:1px solid #ddd;margin-bottom:25px;">
      <p style="margin:0;">📝 <strong>Jouw keuze:</strong> ${choice}</p>
    </div>
    <h3 style="margin-top:0;">Programma</h3>
    ${program}
    ${videoBlock}
    <p style="margin-top:25px;">Gebruik de knop hieronder of de bijlage om het in je agenda te zetten:</p>
    ${button(googleCalendarUrl(lecture, attendance), "📅 Zet in Google Agenda")}
    ${paymentBlock}
    <p style="margin-top:25px;">Toch verhinderd of wil je je keuze wijzigen? <a href="${esc(cancelUrl)}">Meld je hier af</a>, of <a href="${esc(lectureUrl)}">meld je opnieuw aan</a> met hetzelfde e-mailadres.</p>
    <p>Tot dan!<br>Groet,<br><strong>EU Studiegroep</strong> 🇪🇺</p>
  </body></html>`;

  const text = [
    `Beste ${registration.first_name},`,
    "",
    `Leuk dat je erbij bent op ${longDate(lecture.date)}!`,
    `Jouw keuze: ${choice}`,
    `Aanvang: ${attendance.start} bij ${attendance.placeName}`,
    lecture.video_url ? `Videolink: ${lecture.video_url}` : "",
    "",
    `Afmelden: ${cancelUrl}`,
    "",
    "Groet,",
    "EU Studiegroep",
  ].join("\n");

  return sendMail({
    to: registration.email,
    subject: `EU ${lectureTitle(lecture.date)}: bevestiging ${shortDate(lecture.date)}`,
    html,
    text,
    attachments: [{ filename: "invite.ics", content: attendeeIcs(lecture, attendance, siteUrl), contentType: "text/calendar; charset=utf-8; method=PUBLISH" }],
  });
}
