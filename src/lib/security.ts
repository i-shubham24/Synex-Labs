// Central security helpers for this project.
//
// Applicability note (honest surface review, Oct 2026):
// - No database / SQL anywhere -> SQL injection N/A (no query layer to inject).
// - No auth, sessions, JWT, passwords, or cookies -> JWT/password/MFA/CSRF-token
//   storage N/A. Theme only ("light"/"dark") lives in localStorage, never tokens.
// - No file-upload, webhook, or object API -> BOLA/SSRF/signature checks N/A
//   until such endpoints exist. Stubs below are ready for that day.
// - What IS enforced: strict headers + CSP (next.config), same-origin contact
//   API with honeypot, fill-time check and rate limiting, server-side
//   validation, redacted logs, tight CORS, no source maps, no secrets
//   client-side.

const MAX_LEN = { name: 100, email: 254, need: 40, message: 2000 } as const;
const EMAIL_RE = /^[^\s@]{1,64}@[^\s@]{1,253}\.[^\s@]{2,}$/;
const NEEDS = ["Website", "Online store", "Web app", "AI tool", "Not sure yet"] as const;

export type ContactInput = {
  name: string;
  email: string;
  need: string;
  message: string;
  /** Honeypot. Real users never fill this. Bots do. */
  company?: string;
};

// A person needs well over this long to type a name, an email and a message.
const MIN_FILL_MS = 3000;

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
  // Honeypot, or a form sent faster than anyone can type (or with no timing
  // at all, which only a script posting straight to the API would do):
  // pretend success so bots learn nothing.
  const tooFast = typeof r.elapsed !== "number" || r.elapsed < MIN_FILL_MS;
  if ((typeof r.company === "string" && r.company.trim() !== "") || tooFast)
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

// --- Fixed-window rate limit. Uses Upstash Redis when its REST URL and token
// are set, so every server instance shares one count. Otherwise, or if Redis
// is unreachable, falls back to a per-instance in-memory window. ---
const buckets = new Map<string, { count: number; reset: number }>();

export type RateLimitInfo = {
  allowed: boolean;
  retryAfter: number;
  limit: number;
  remaining: number;
  /** Epoch seconds when the window resets (for X-RateLimit-Reset). */
  reset: number;
};

async function sharedHit(
  key: string,
  windowMs: number,
): Promise<{ count: number; reset: number } | null> {
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!url || !token) return null;
  const k = `rl:${key}`;
  try {
    const res = await fetch(`${url.replace(/\/$/, "")}/pipeline`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      // Start the window only if it is not running, then count this hit.
      body: JSON.stringify([
        ["SET", k, "0", "PX", String(windowMs), "NX"],
        ["INCR", k],
        ["PTTL", k],
      ]),
      signal: AbortSignal.timeout(2000),
      cache: "no-store",
    });
    if (!res.ok) return null;
    const [, count, ttl] = (await res.json()) as { result: number }[];
    if (typeof count?.result !== "number") return null;
    return { count: count.result, reset: Date.now() + Math.max(0, ttl?.result ?? windowMs) };
  } catch {
    return null;
  }
}

export async function rateLimit(
  key: string,
  limit = 5,
  windowMs = 60_000,
): Promise<RateLimitInfo> {
  const now = Date.now();
  const shared = await sharedHit(key, windowMs);
  if (shared) {
    const allowed = shared.count <= limit;
    return {
      allowed,
      retryAfter: allowed ? 0 : Math.ceil((shared.reset - now) / 1000),
      limit,
      remaining: Math.max(0, limit - shared.count),
      reset: Math.ceil(shared.reset / 1000),
    };
  }
  // Drop expired windows so a stream of new IPs cannot grow the map forever.
  if (buckets.size > 5000)
    for (const [k, v] of buckets) if (now > v.reset) buckets.delete(k);
  const hit = buckets.get(key);
  if (!hit || now > hit.reset) {
    buckets.set(key, { count: 1, reset: now + windowMs });
    return {
      allowed: true,
      retryAfter: 0,
      limit,
      remaining: limit - 1,
      reset: Math.ceil((now + windowMs) / 1000),
    };
  }
  const reset = Math.ceil(hit.reset / 1000);
  if (hit.count >= limit)
    return {
      allowed: false,
      retryAfter: Math.ceil((hit.reset - now) / 1000),
      limit,
      remaining: 0,
      reset,
    };
  hit.count += 1;
  return {
    allowed: true,
    retryAfter: 0,
    limit,
    remaining: limit - hit.count,
    reset,
  };
}

// --- Idempotency store (in-memory, per instance). Retried or double-clicked
// submissions carry an Idempotency-Key; the server processes it once and
// replays the success response. Swap for Redis when running mutiple nodes. ---
const seenKeys = new Map<string, number>();
const IDEM_KEY_RE = /^[A-Za-z0-9-]{8,64}$/;
const IDEM_MAX_KEYS = 1000;

/**
 * Records an idempotency key. Returns true when this is the first seen
 * request for the key (process it), false when it is a replay (return the
 * cached answer instead). Unparsable / missing keys fall through so the
 * rate limiter governs those requests.
 */
export function firstTime(key: string | null, ttlMs = 10 * 60_000): boolean {
  if (!key || !IDEM_KEY_RE.test(key)) return true;
  const now = Date.now();
  if (seenKeys.size >= IDEM_MAX_KEYS) {
    for (const [k, exp] of [...seenKeys]) {
      if (exp <= now) seenKeys.delete(k);
    }
    while (seenKeys.size >= IDEM_MAX_KEYS) {
      const oldest = seenKeys.keys().next();
      if (oldest.done === true) break;
      seenKeys.delete(oldest.value);
    }
  }
  const exp = seenKeys.get(key);
  if (exp !== undefined && exp > now) return false;
  seenKeys.set(key, now + ttlMs);
  return true;
}

/** Forgets a key whose request failed, so a retry is processed again. */
export function forgetKey(key: string | null) {
  if (key) seenKeys.delete(key);
}

/**
 * Reads a request body as JSON, giving up once it passes `max` bytes so an
 * oversized upload is never buffered whole. Returns `undefined` when the body
 * is too large and throws when it is not valid JSON.
 */
export async function readJsonCapped(req: Request, max: number): Promise<unknown> {
  if (Number(req.headers.get("content-length") ?? 0) > max) return undefined;
  const reader = req.body?.getReader();
  if (!reader) return JSON.parse("");
  const chunks: Uint8Array[] = [];
  let size = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > max) {
      await reader.cancel();
      return undefined;
    }
    chunks.push(value);
  }
  const bytes = new Uint8Array(size);
  let at = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, at);
    at += chunk.byteLength;
  }
  return JSON.parse(new TextDecoder().decode(bytes));
}

export function clientIp(headers: Headers): string {
  return (
    headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    headers.get("x-real-ip") ||
    "unknown"
  );
}

/**
 * Same-origin guard: browsers send Origin/Referer on fetch POSTs. The form may
 * be served from the canonical domain or from the host this request reached
 * (localhost, a preview deploy). A browser always sends the real Host, so a
 * cross-site page still fails the check.
 */
export function isSameOrigin(req: Request, siteUrl: string): boolean {
  const origin = req.headers.get("origin");
  const referer = req.headers.get("referer");
  if (!origin && !referer) return true; // non-browser / curl: let rate limit decide
  try {
    const allowed = new Set([new URL(siteUrl).origin, new URL(req.url).origin]);
    return allowed.has(new URL(origin ?? referer ?? "").origin);
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
