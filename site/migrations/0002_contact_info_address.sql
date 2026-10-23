-- Public contact address moves from the Gmail inbox to info@studiegroep.eu (forwarded to Gmail by Cloudflare Email Routing).
UPDATE settings SET value = 'info@studiegroep.eu' WHERE key = 'contact_email' AND value = 'eustudiegroep@gmail.com';
