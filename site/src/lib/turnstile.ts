import { env } from "cloudflare:workers";

/** Verifies the Turnstile token from the signup form. Skipped when no secret is configured (local development). */
export async function verifyTurnstile(token: FormDataEntryValue | null, ip: string | undefined): Promise<boolean> {
  if (!env.TURNSTILE_SECRET_KEY) return true;
  if (typeof token !== "string" || !token) return false;
  const body = new FormData();
  body.append("secret", env.TURNSTILE_SECRET_KEY);
  body.append("response", token);
  if (ip) body.append("remoteip", ip);
  const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", { method: "POST", body });
  const result = (await response.json()) as { success: boolean };
  return result.success;
}
