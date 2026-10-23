import type { APIRoute } from "astro";
import { getLecture, getRegistrations } from "../../../../lib/db";

const cell = (value: string | number | null) => {
  const text = String(value ?? "");
  // Quote everything, and defuse values Excel would read as formulas.
  return `"${(/^[=+\-@]/.test(text) ? `'${text}` : text).replace(/"/g, '""')}"`;
};

export const GET: APIRoute = async ({ params }) => {
  const lecture = await getLecture(Number(params.id));
  if (!lecture) return new Response("Niet gevonden", { status: 404 });
  const rows = await getRegistrations(lecture.id);
  const lines = [
    ["Voornaam", "Achternaam", "Email", "Status", "Diner", "Aangemeld", "Gewijzigd"],
    ...rows.map((r) => [r.first_name, r.last_name, r.email, r.status, r.dinner ? "ja" : "nee", r.created_at, r.updated_at]),
  ];
  // Semicolons and a BOM so Dutch Excel opens it in columns with accents intact.
  const csv = "﻿" + lines.map((line) => line.map(cell).join(";")).join("\r\n");
  return new Response(csv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="aanmeldingen-${lecture.slug}.csv"`,
    },
  });
};
