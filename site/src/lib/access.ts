import { env } from "cloudflare:workers";

interface Jwk extends JsonWebKey {
  kid: string;
}

let cachedKeys: { keys: Jwk[]; fetchedAt: number } | null = null;

async function accessKeys(): Promise<Jwk[]> {
  if (cachedKeys && Date.now() - cachedKeys.fetchedAt < 60 * 60 * 1000) return cachedKeys.keys;
  const response = await fetch(`${env.ACCESS_TEAM_DOMAIN}/cdn-cgi/access/certs`);
  const { keys } = (await response.json()) as { keys: Jwk[] };
  cachedKeys = { keys, fetchedAt: Date.now() };
  return keys;
}

function base64UrlDecode(value: string): Uint8Array<ArrayBuffer> {
  const base64 = value.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(value.length / 4) * 4, "=");
  return Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
}

/**
 * Returns the email of the person Cloudflare Access signed in, after checking the
 * Cf-Access-Jwt-Assertion token's signature, audience and expiry. Null when anything is off.
 */
export async function accessEmail(request: Request): Promise<string | null> {
  const token = request.headers.get("Cf-Access-Jwt-Assertion");
  if (!token || !env.ACCESS_AUD) return null;
  const [headerPart, payloadPart, signaturePart] = token.split(".");
  if (!headerPart || !payloadPart || !signaturePart) return null;

  try {
    const header = JSON.parse(new TextDecoder().decode(base64UrlDecode(headerPart))) as { kid: string; alg: string };
    if (header.alg !== "RS256") return null;
    const jwk = (await accessKeys()).find((k) => k.kid === header.kid);
    if (!jwk) return null;

    const key = await crypto.subtle.importKey("jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
    const valid = await crypto.subtle.verify(
      "RSASSA-PKCS1-v1_5",
      key,
      base64UrlDecode(signaturePart),
      new TextEncoder().encode(`${headerPart}.${payloadPart}`),
    );
    if (!valid) return null;

    const payload = JSON.parse(new TextDecoder().decode(base64UrlDecode(payloadPart))) as {
      aud: string | string[];
      exp: number;
      iss: string;
      email?: string;
    };
    const audiences = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
    if (!audiences.includes(env.ACCESS_AUD)) return null;
    if (payload.iss !== env.ACCESS_TEAM_DOMAIN) return null;
    if (payload.exp * 1000 < Date.now()) return null;
    return payload.email?.toLowerCase() ?? null;
  } catch {
    return null;
  }
}
