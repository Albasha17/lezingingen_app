-- Sample data for local development: npx wrangler d1 execute studiegroep --local --file seed/dev.sql
INSERT INTO lectures (slug, date, time_dinner, time_lecture, time_end, speaker_name, speaker_role, speaker_bio,
  dinner_name, dinner_address, lecture_name, lecture_address, video_url, payment_url)
VALUES
  ('2026-11-voorbeeld', '2026-11-19', '18:00', '19:30', '21:00', 'Voorbeeld Spreker', 'Beleidsmedewerker, Europese Commissie',
   'Korte biografie van de spreker. Wordt later via het beheerscherm ingevuld.',
   'Restaurant & Pizzeria Lucca Due', 'Haarlemmerstraat 130, Amsterdam', 'De Piramide', 'Haarlemmer Houttuinen, Amsterdam',
   'https://meet.google.com/', 'https://bunq.me/'),
  ('2026-09-voorbeeld', '2026-09-17', '18:00', '19:30', '21:00', 'Eerdere Spreker', 'Europarlementariër',
   'Een lezing uit het archief.',
   'Restaurant & Pizzeria Lucca Due', 'Haarlemmerstraat 130, Amsterdam', 'De Piramide', 'Haarlemmer Houttuinen, Amsterdam',
   NULL, NULL);
