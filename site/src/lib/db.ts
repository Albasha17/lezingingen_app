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
  online: number;
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

export type RegistrationStatus = "fysiek" | "online" | "afgemeld";

export interface Registration {
  id: number;
  lecture_id: number;
  first_name: string;
  last_name: string;
  email: string | null;
  status: RegistrationStatus;
  dinner: number;
  cancel_token: string;
  email_sent_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RegistrationInput {
  lectureId: number;
  firstName: string;
  lastName: string;
  email: string | null;
  status: RegistrationStatus;
  dinner: boolean;
}

/**
 * Stores a registration. A second signup with the same email for the same lecture
 * updates the earlier one, so people can change their choice by signing up again.
 */
export async function saveRegistration(input: RegistrationInput): Promise<Registration> {
  const existing = input.email
    ? await env.DB.prepare("SELECT * FROM registrations WHERE lecture_id = ? AND email = ?")
        .bind(input.lectureId, input.email)
        .first<Registration>()
    : null;

  if (existing) {
    return (await env.DB.prepare(
      `UPDATE registrations SET first_name = ?, last_name = ?, status = ?, dinner = ?, updated_at = datetime('now')
       WHERE id = ? RETURNING *`,
    )
      .bind(input.firstName, input.lastName, input.status, input.dinner ? 1 : 0, existing.id)
      .first<Registration>())!;
  }

  return (await env.DB.prepare(
    `INSERT INTO registrations (lecture_id, first_name, last_name, email, status, dinner, cancel_token)
     VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING *`,
  )
    .bind(input.lectureId, input.firstName, input.lastName, input.email, input.status, input.dinner ? 1 : 0, crypto.randomUUID())
    .first<Registration>())!;
}

export async function markEmailSent(id: number): Promise<void> {
  await env.DB.prepare("UPDATE registrations SET email_sent_at = datetime('now') WHERE id = ?").bind(id).run();
}

export async function getRegistrationByToken(token: string): Promise<Registration | null> {
  return env.DB.prepare("SELECT * FROM registrations WHERE cancel_token = ?").bind(token).first<Registration>();
}

export async function getRegistration(id: number): Promise<Registration | null> {
  return env.DB.prepare("SELECT * FROM registrations WHERE id = ?").bind(id).first<Registration>();
}

export async function cancelRegistration(id: number): Promise<void> {
  await env.DB.prepare("UPDATE registrations SET status = 'afgemeld', dinner = 0, updated_at = datetime('now') WHERE id = ?")
    .bind(id)
    .run();
}

export async function deleteRegistration(id: number): Promise<void> {
  await env.DB.prepare("DELETE FROM registrations WHERE id = ?").bind(id).run();
}

export async function getRegistrations(lectureId: number): Promise<Registration[]> {
  const { results } = await env.DB.prepare(
    "SELECT * FROM registrations WHERE lecture_id = ? ORDER BY status = 'afgemeld', last_name COLLATE NOCASE, first_name COLLATE NOCASE",
  )
    .bind(lectureId)
    .all<Registration>();
  return results;
}

export interface Counts {
  fysiek: number;
  dinner: number;
  online: number;
  afgemeld: number;
}

export function countRegistrations(rows: Registration[]): Counts {
  return {
    fysiek: rows.filter((r) => r.status === "fysiek").length,
    dinner: rows.filter((r) => r.status === "fysiek" && r.dinner).length,
    online: rows.filter((r) => r.status === "online").length,
    afgemeld: rows.filter((r) => r.status === "afgemeld").length,
  };
}

export async function getCountsByLecture(): Promise<Map<number, Counts>> {
  const { results } = await env.DB.prepare(
    `SELECT lecture_id,
            SUM(status = 'fysiek') AS fysiek,
            SUM(status = 'fysiek' AND dinner = 1) AS dinner,
            SUM(status = 'online') AS online,
            SUM(status = 'afgemeld') AS afgemeld
     FROM registrations GROUP BY lecture_id`,
  ).all<Counts & { lecture_id: number }>();
  return new Map(results.map(({ lecture_id, ...counts }) => [lecture_id, counts]));
}

// --- Lectures (admin) ---

export async function getAllLectures(): Promise<Lecture[]> {
  const { results } = await env.DB.prepare("SELECT * FROM lectures ORDER BY date DESC").all<Lecture>();
  return results;
}

export async function getLecture(id: number): Promise<Lecture | null> {
  return env.DB.prepare("SELECT * FROM lectures WHERE id = ?").bind(id).first<Lecture>();
}

export type LectureInput = Omit<Lecture, "id">;

const LECTURE_COLUMNS = [
  "slug", "date", "time_dinner", "time_lecture", "time_end", "speaker_name", "speaker_role", "speaker_bio",
  "speaker_linkedin", "image_key", "dinner_name", "dinner_address", "dinner_maps_url", "lecture_name",
  "lecture_address", "lecture_maps_url", "online", "video_url", "payment_url", "signup_open",
] as const satisfies readonly (keyof LectureInput)[];

export async function createLecture(input: LectureInput): Promise<Lecture> {
  const placeholders = LECTURE_COLUMNS.map(() => "?").join(", ");
  return (await env.DB.prepare(`INSERT INTO lectures (${LECTURE_COLUMNS.join(", ")}) VALUES (${placeholders}) RETURNING *`)
    .bind(...LECTURE_COLUMNS.map((c) => input[c]))
    .first<Lecture>())!;
}

export async function updateLecture(id: number, input: LectureInput): Promise<void> {
  const assignments = LECTURE_COLUMNS.map((c) => `${c} = ?`).join(", ");
  await env.DB.prepare(`UPDATE lectures SET ${assignments} WHERE id = ?`)
    .bind(...LECTURE_COLUMNS.map((c) => input[c]), id)
    .run();
}

export async function deleteLecture(id: number): Promise<void> {
  await env.DB.batch([
    env.DB.prepare("DELETE FROM registrations WHERE lecture_id = ?").bind(id),
    env.DB.prepare("DELETE FROM lectures WHERE id = ?").bind(id),
  ]);
}

// --- Admins ---

export interface Admin {
  email: string;
  role: "owner" | "admin";
  added_by: string | null;
  created_at: string;
}

export async function getAdmin(email: string): Promise<Admin | null> {
  return env.DB.prepare("SELECT * FROM admins WHERE email = ?").bind(email.toLowerCase()).first<Admin>();
}

export async function getAdmins(): Promise<Admin[]> {
  const { results } = await env.DB.prepare("SELECT * FROM admins ORDER BY role DESC, email").all<Admin>();
  return results;
}

export async function addAdmin(email: string, role: Admin["role"], addedBy: string): Promise<void> {
  await env.DB.prepare(
    "INSERT INTO admins (email, role, added_by) VALUES (?, ?, ?) ON CONFLICT(email) DO UPDATE SET role = excluded.role",
  )
    .bind(email.toLowerCase(), role, addedBy)
    .run();
}

export async function removeAdmin(email: string): Promise<void> {
  await env.DB.prepare("DELETE FROM admins WHERE email = ?").bind(email.toLowerCase()).run();
}

export async function saveSettings(values: Record<string, string>): Promise<void> {
  await env.DB.batch(
    Object.entries(values).map(([key, value]) =>
      env.DB.prepare("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value").bind(key, value),
    ),
  );
}
