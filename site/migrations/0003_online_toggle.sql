-- Explicit switch for the online option, so it can be on before the stream link is known.
ALTER TABLE lectures ADD COLUMN online INTEGER NOT NULL DEFAULT 0;
UPDATE lectures SET online = 1 WHERE video_url IS NOT NULL AND video_url <> '';
