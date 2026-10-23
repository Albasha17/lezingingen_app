const ENTITIES: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

/** Escapes text for HTML built as strings (emails, Mailchimp export). Astro templates escape on their own. */
export function esc(value: string | null | undefined): string {
  return (value ?? "").replace(/[&<>"']/g, (c) => ENTITIES[c]);
}
