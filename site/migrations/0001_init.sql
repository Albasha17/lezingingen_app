-- Lectures replace the "Config" tab; registrations replace the per-lecture Aanmeldingen tabs.
CREATE TABLE lectures (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL UNIQUE,
  date TEXT NOT NULL,              -- YYYY-MM-DD
  time_dinner TEXT,                -- HH:MM, NULL when there is no dinner
  time_lecture TEXT NOT NULL,      -- HH:MM
  time_end TEXT NOT NULL,          -- HH:MM
  speaker_name TEXT NOT NULL,
  speaker_role TEXT NOT NULL DEFAULT '',
  speaker_bio TEXT NOT NULL DEFAULT '',
  speaker_linkedin TEXT,
  image_key TEXT,                  -- R2 object key or absolute URL
  dinner_name TEXT,
  dinner_address TEXT,
  dinner_maps_url TEXT,
  lecture_name TEXT NOT NULL,
  lecture_address TEXT NOT NULL,
  lecture_maps_url TEXT,
  video_url TEXT,
  payment_url TEXT,
  signup_open INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE registrations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lecture_id INTEGER NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  email TEXT,                      -- optional for afmeldingen
  status TEXT NOT NULL CHECK (status IN ('fysiek', 'online', 'afgemeld')),
  dinner INTEGER NOT NULL DEFAULT 0,
  cancel_token TEXT NOT NULL UNIQUE,
  email_sent_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- One registration per email per lecture; a second signup updates the first.
CREATE UNIQUE INDEX registrations_lecture_email ON registrations(lecture_id, lower(email)) WHERE email IS NOT NULL;
CREATE INDEX registrations_lecture ON registrations(lecture_id);

CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

INSERT INTO settings (key, value) VALUES
  ('contact_email', 'eustudiegroep@gmail.com'),
  ('price_single', '10'),
  ('price_half_season', '40'),
  ('price_full_season', '60');
