// Central security helpers for this project.
//
// Applicability note (honest surface review, Oct 2026):
// - No database / SQL anywhere -> SQL injection N/A (no query layer to inject).
// - No auth, sessions, JWT, passwords, or cookies -> JWT/password/MFA/CSRF-token
//   storage N/A. Theme only ("light"/"dark") lives in localStorage, never tokens.
// - No file-upload, webhook, or object API -> BOLA/SSRF/signature checks N/A
//   until such endpoints exist. Stubs below are ready for that day.
// - What IS enforced: strict headers + CSP (next.config), same-origin contact
//   API with honeypot + rate limiting, server-side validation, redacted logs,
//   tight CORS, no source maps, no secrets client-side.

const MAX_LEN = { name: 100, email: 254, need: 40, message: 2000 } as const;
const EMAIL_RE = /^[^\s@]{1,64}@[^\s@]{1,253}\.[^\s@]{2,}$/;
const NEEDS = ["Website", "Online store", "Web app", "AI tool", "Not sure yet"] as const;

export type ContactInput = {
  name: string;
  email: string;
  need: string;
  message: string;
  /** Honeypot — real users never fill this. Bots do. */
  company?: string;
};

/** Strip angle brackets / control chars so reflected values can't break HTML. */
export function sanitizeText(value: unknown, max: number): string {
  return String(value ?? "")
    .replace(/[\u0000-\u001f\u007f<>]/g, "")
    .trim()
    .slice(0, max);
}

export function validateContact(raw: unknown): {
  ok: boolean;
  data?: ContactInput;
  error?: string;
} {
  if (typeof raw !== "object" || raw === null)
    return { ok: false, error: "Invalid payload." };
  const r = raw as Record<string, unknown>;
  // Honeypot: pretend success so bots learn nothing.
  if (typeof r.company === "string" && r.company.trim() !== "")
    return {
      ok: true,
      data: { name: "", email: "", need: "", message: "", company: "bot" },
    };
  const data: ContactInput = {
    name: sanitizeText(r.name, MAX_LEN.name),
    email: sanitizeText(r.email, MAX_LEN.email).toLowerCase(),
    need: sanitizeText(r.need, MAX_LEN.need),
    message: sanitizeText(r.message, MAX_LEN.message),
  };
  if (data.name.length < 2) return { ok: false, error: "Please add your name." };
  if (!EMAIL_RE.test(data.email))
    return { ok: false, error: "That email does not look right." };
  if (!(NEEDS as readonly string[]).includes(data.need))
    return { ok: false, error: "Pick one of the listed needs." };
  if (data.message.length < 10)
    return { ok: false, error: "Tell us a little more (10+ characters)." };
  return { ok: true, data };
}

// --- Tiny in-memory token bucket (per runtime instance). Good enough for a
// low-traffic contact form; swap for Redis/Upstash when scaling. ---
const buckets = new Map<string, { count: number; reset: number }>();

export function rateLimit(key: string, limit = 5, windowMs = 60_000): {
  allowed: boolean;
  retryAfter: number;
} {
  const now = Date.now();
  const hit = buckets.get(key);
  if (!hit || now > hit.reset) {
    buckets.set(key, { count: 1, reset: now + windowMs });
    return { allowed: true, retryAfter: 0 };
  }
  if (hit.count >= limit)
    return { allowed: false, retryAfter: Math.ceil((hit.reset - now) / 1000) };
  hit.count += 1;
  return { allowed: true, retryAfter: 0 };
}

export function clientIp(headers: Headers): string {
  return (
    headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    headers.get("x-real-ip") ||
    "unknown"
  );
}

/** Same-origin guard: browsers send Origin/Referer on fetch POSTs. */
export function isSameOrigin(req: Request, siteUrl: string): boolean {
  const origin = req.headers.get("origin");
  const referer = req.headers.get("referer");
  if (!origin && !referer) return true; // non-browser / curl: let rate limit decide
  try {
    const site = new URL(siteUrl).origin;
    if (origin && new URL(origin).origin !== site) return false;
    if (!origin && referer && new URL(referer).origin !== site) return false;
    return true;
  } catch {
    return false;
  }
}

/** Tight CORS: same-origin only. No `*`, no credentials for third parties. */
export function corsHeaders(origin: string | null, siteUrl: string): HeadersInit {
  try {
    const site = new URL(siteUrl).origin;
    if (origin && new URL(origin).origin === site)
      return {
        "Access-Control-Allow-Origin": site,
        Vary: "Origin",
      };
  } catch {
    /* fall through: no CORS headers */
  }
  return { Vary: "Origin" };
}

/** Redacted logger: never log names, emails, or message bodies. */
export function logContactEvent(event: string, fields: Record<string, unknown>) {
  const safe: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(fields)) {
    if (["name", "email", "message", "body"].includes(k)) safe[k] = "[redacted]";
    else safe[k] = v;
  }
  console.log(JSON.stringify({ event, ...safe }));
}

// --- Future file-upload validator (no upload endpoint exists today). ---
const ALLOWED_UPLOAD_MIME = new Set([
  "image/png",
  "image/jpeg",
  "image/webp",
  "application/pdf",
]);

export function validateUpload(file: {
  size: number;
  type: string;
  name: string;
}): { ok: boolean; error?: string } {
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  const safeName = /^[a-z0-9][a-z0-9._-]{0,100}$/i.test(file.name);
  if (!safeName || ["exe", "js", "html", "svg"].includes(ext))
    return { ok: false, error: "File type not allowed." };
  if (!ALLOWED_UPLOAD_MIME.has(file.type))
    return { ok: false, error: "MIME type not allowed." };
  if (file.size <= 0 || file.size > 5 * 1024 * 1024)
    return { ok: false, error: "File must be 1 byte – 5 MB." };
  // Serve uploads with `Content-Disposition: attachment` + `nosniff`, never inline.
  return { ok: true };
}

// --- Future webhook signature check (no webhooks today). Keeps the pattern
// ready: HMAC-SHA256 over raw body, constant-time compare. ---
export async function verifyHmacSignature(
  rawBody: string,
  signatureHex: string,
  secret: string,
): Promise<boolean> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const mac = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(rawBody),
  );
  const hex = [...new Uint8Array(mac)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  if (hex.length !== signatureHex.length) return false;
  let diff = 0;
  for (let i = 0; i < hex.length; i++) diff |= hex.charCodeAt(i) ^ signatureHex.charCodeAt(i);
  return diff === 0;
}
