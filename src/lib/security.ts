import { servicePackages } from "@/data/packages";

// ============================================================================
// OWASP 2025 ZERO-TRUST SECURITY ENGINE & SANITIZATION SUITE
// ============================================================================

const MAX_LEN = { name: 100, email: 254, need: 40, message: 2000 } as const;
const EMAIL_RE = /^[^\s@]{1,64}@[^\s@]{1,253}\.[^\s@]{2,}$/;
const NEEDS = ["Website", "Online store", "Web app", "AI tool", "Not sure yet"] as const;

export type ContactInput = {
  name: string;
  email: string;
  need: string;
  message: string;
  /** Invisible honeypot field. Real users never fill this; bots do. */
  company?: string;
  hp_website?: string;
};

// Real users need well over 3000ms to parse, type name/email, and compose a message.
export const MIN_FILL_MS = 3000;

// ----------------------------------------------------------------------------
// 1. RECURSIVE NoSQL / SQL INJECTION & PROTOTYPE POLLUTION SANITIZER
// ----------------------------------------------------------------------------

const FORBIDDEN_KEYS = new Set(["__proto__", "constructor", "prototype"]);

/**
 * Strips non-printable ASCII control characters (0x00-0x1F, 0x7F) and HTML angle
 * brackets (<, >) to neutralize reflected/stored XSS vectors.
 */
export function sanitizeText(value: unknown, max = 2000): string {
  return String(value ?? "")
    .replace(/[\u0000-\u001f\u007f<>]/g, "")
    .trim()
    .slice(0, max);
}

/**
 * Recursively deep-sanitizes unknown incoming JSON payloads:
 * - Drops prototype pollution vectors (__proto__, constructor, prototype).
 * - Strips MongoDB / NoSQL injection operators (keys starting with $).
 * - Strips dot-notation property path injection (keys containing dots).
 * - Recursively cleans strings, stripping control characters and angle brackets.
 */
export function sanitizePayload<T = unknown>(input: T): T {
  if (input === null || typeof input !== "object") {
    if (typeof input === "string") {
      return sanitizeText(input, 5000) as unknown as T;
    }
    return input;
  }

  if (Array.isArray(input)) {
    return input.map((item) => sanitizePayload(item)) as unknown as T;
  }

  const cleanObj: Record<string, unknown> = {};
  for (const [key, val] of Object.entries(input as Record<string, unknown>)) {
    // 1. Prototype pollution protection
    if (FORBIDDEN_KEYS.has(key)) continue;

    // 2. NoSQL injection operator stripping ($where, $gt, $regex, etc.)
    if (key.startsWith("$")) continue;

    // 3. Dot notation object manipulation defense
    if (key.includes(".")) continue;

    // 4. Recursive sanitization
    cleanObj[key] = sanitizePayload(val);
  }

  return cleanObj as T;
}

// ----------------------------------------------------------------------------
// 2. CONTACT FORM VALIDATOR & BOT HONEYPOT DEFENSE
// ----------------------------------------------------------------------------

export function validateContact(raw: unknown): {
  ok: boolean;
  data?: ContactInput;
  error?: string;
  isBot?: boolean;
} {
  if (typeof raw !== "object" || raw === null) {
    return { ok: false, error: "Invalid payload." };
  }

  // Deep sanitize payload first
  const sanitized = sanitizePayload(raw as Record<string, unknown>);
  const r = sanitized as Record<string, unknown>;

  // Honeypot detection: check both company and hp_website
  const hasHoneypotValue =
    (typeof r.company === "string" && r.company.trim() !== "") ||
    (typeof r.hp_website === "string" && r.hp_website.trim() !== "") ||
    (typeof r.website === "string" && r.website.trim() !== "") ||
    (typeof r.url === "string" && r.url.trim() !== "");

  // Timing defense: submissions faster than human typing threshold
  const elapsed = typeof r.elapsed === "number" ? r.elapsed : 0;
  const isTooFast = elapsed < MIN_FILL_MS;

  if (hasHoneypotValue || isTooFast) {
    // Return fake success so bots and scrapers receive no actionable feedback
    return {
      ok: true,
      isBot: true,
      data: { name: "", email: "", need: "", message: "", company: "bot" },
    };
  }

  const data: ContactInput = {
    name: sanitizeText(r.name, MAX_LEN.name),
    email: sanitizeText(r.email, MAX_LEN.email).toLowerCase(),
    need: sanitizeText(r.need, MAX_LEN.need),
    message: sanitizeText(r.message, MAX_LEN.message),
  };

  if (data.name.length < 2) return { ok: false, error: "Please add your name." };
  if (!EMAIL_RE.test(data.email))
    return { ok: false, error: "That email does not look right." };
  if (!(NEEDS as readonly string[]).includes(data.need as (typeof NEEDS)[number]))
    return { ok: false, error: "Pick one of the listed needs." };
  if (data.message.length < 10)
    return { ok: false, error: "Tell us a little more (10+ characters)." };

  return { ok: true, data, isBot: false };
}

// ----------------------------------------------------------------------------
// 3. BROKEN OBJECT-LEVEL AUTHORIZATION (BOLA / IDOR) DEFENSE
// ----------------------------------------------------------------------------

/**
 * Constant-time comparison to prevent timing attacks.
 */
export function timingSafeEqualString(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}

/**
 * Verifies that the authenticated session user strictly owns the target resource ID.
 */
export function assertOwnership(
  resourceOwnerId: string,
  sessionUserId: string,
): boolean {
  if (!resourceOwnerId || !sessionUserId) return false;
  return timingSafeEqualString(resourceOwnerId, sessionUserId);
}

/**
 * Drops privileged or client-tampered role attributes (userId, role, isAdmin, permissions).
 */
export function stripPrivilegedClaims<T extends Record<string, unknown>>(body: T): T {
  const untrustedKeys = ["userId", "role", "roles", "isAdmin", "isSuperAdmin", "permissions", "scope"];
  const sanitized = { ...body };
  for (const key of untrustedKeys) {
    delete sanitized[key];
  }
  return sanitized;
}

/**
 * Generates a cryptographically signed HMAC token for guest inquiry verification.
 */
export async function generateInquiryToken(
  inquiryId: string,
  email: string,
  secret = process.env.AUTH_SECRET || "synex-inquiry-token-secret-fallback",
): Promise<string> {
  const payload = `${inquiryId}:${email.toLowerCase()}`;
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(payload),
  );
  return [...new Uint8Array(signature)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * Verifies the guest inquiry cryptographic token in constant time.
 */
export async function verifyInquiryToken(
  inquiryId: string,
  email: string,
  token: string,
  secret = process.env.AUTH_SECRET || "synex-inquiry-token-secret-fallback",
): Promise<boolean> {
  const expected = await generateInquiryToken(inquiryId, email, secret);
  return timingSafeEqualString(expected, token);
}

// ----------------------------------------------------------------------------
// 4. SERVER-SIDE PRICE & TRANSACTION INTEGRITY
// ----------------------------------------------------------------------------

export type OrderItem = {
  packageId: string;
  quantity: number;
};

export type ValidatedOrder = {
  valid: boolean;
  subtotal: number;
  discount: number;
  tax: number;
  total: number;
  currency: string;
  items: {
    packageId: string;
    name: string;
    unitPrice: number;
    quantity: number;
    total: number;
  }[];
  error?: string;
};

/**
 * Validates checkout payloads server-side. Resolves canonical package prices
 * from the immutable catalog. Never trusts client-submitted prices or totals.
 */
export function calculateOrderTotal(
  items: OrderItem[],
  discountCode?: string,
): ValidatedOrder {
  if (!Array.isArray(items) || items.length === 0) {
    return { valid: false, subtotal: 0, discount: 0, tax: 0, total: 0, currency: "USD", items: [], error: "No items provided." };
  }

  let subtotal = 0;
  const validatedItems: ValidatedOrder["items"] = [];

  for (const item of items) {
    const pkg = servicePackages.find((p) => p.id === item.packageId);
    if (!pkg) {
      return { valid: false, subtotal: 0, discount: 0, tax: 0, total: 0, currency: "USD", items: [], error: `Unknown package: ${item.packageId}` };
    }

    const qty = Math.floor(Number(item.quantity));
    if (isNaN(qty) || qty < 1 || qty > 100) {
      return { valid: false, subtotal: 0, discount: 0, tax: 0, total: 0, currency: "USD", items: [], error: "Invalid item quantity (must be 1-100)." };
    }

    const itemTotal = pkg.price * qty;
    subtotal += itemTotal;
    validatedItems.push({
      packageId: pkg.id,
      name: pkg.name,
      unitPrice: pkg.price,
      quantity: qty,
      total: itemTotal,
    });
  }

  // Server-side discount codes validation
  let discount = 0;
  if (discountCode) {
    const cleanCode = discountCode.trim().toUpperCase();
    if (cleanCode === "SYNEX10") {
      discount = Math.round(subtotal * 0.1);
    } else if (cleanCode === "LAUNCH20") {
      discount = Math.round(subtotal * 0.2);
    }
  }

  const taxableAmount = Math.max(0, subtotal - discount);
  // Optional 18% standard GST or 0 for export services
  const tax = Math.round(taxableAmount * 0.18);
  const total = taxableAmount + tax;

  return {
    valid: true,
    subtotal,
    discount,
    tax,
    total,
    currency: "USD",
    items: validatedItems,
  };
}

/**
 * Production-grade HMAC-SHA256 signature verification for Stripe / Payment webhooks.
 * Includes replay protection by verifying timestamp within tolerance window (default 300s).
 */
export async function verifyWebhookSignature(
  rawBody: string,
  signatureHeader: string,
  secret: string,
  toleranceSeconds = 300,
): Promise<{ valid: boolean; reason?: string }> {
  if (!signatureHeader || !secret) {
    return { valid: false, reason: "Missing signature header or secret." };
  }

  // Format: t=1614555845,v1=5257a869e7ecebeda32affa62cd4908f483a625b4c4738a...
  const parts = signatureHeader.split(",");
  let timestamp = "";
  const signatures: string[] = [];

  for (const part of parts) {
    const [k, v] = part.trim().split("=");
    if (k === "t") timestamp = v;
    if (k === "v1") signatures.push(v);
  }

  if (!timestamp || signatures.length === 0) {
    return { valid: false, reason: "Invalid signature header format." };
  }

  // Replay attack defense
  const timeNum = parseInt(timestamp, 10);
  const now = Math.floor(Date.now() / 1000);
  if (isNaN(timeNum) || Math.abs(now - timeNum) > toleranceSeconds) {
    return { valid: false, reason: "Webhook timestamp outside tolerance window." };
  }

  const payload = `${timestamp}.${rawBody}`;
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
    new TextEncoder().encode(payload),
  );
  const expectedSig = [...new Uint8Array(mac)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");

  const match = signatures.some((sig) => timingSafeEqualString(sig, expectedSig));
  return { valid: match, reason: match ? undefined : "Signature mismatch." };
}

// ----------------------------------------------------------------------------
// 5. MULTI-TIER RATE LIMITING (DISTRIBUTED UPSTASH + IN-MEMORY FALLBACK)
// ----------------------------------------------------------------------------

export const RATE_LIMIT_TIERS = {
  CONTACT: { limit: 5, windowMs: 60_000 },
  AUTH: { limit: 5, windowMs: 60_000 },
  API: { limit: 60, windowMs: 60_000 },
} as const;

const buckets = new Map<string, { count: number; reset: number }>();

export type RateLimitInfo = {
  allowed: boolean;
  retryAfter: number;
  limit: number;
  remaining: number;
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

  // In-memory bounded Map fallback
  if (buckets.size > 5000) {
    for (const [k, v] of buckets) {
      if (now > v.reset) buckets.delete(k);
    }
  }

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
  if (hit.count >= limit) {
    return {
      allowed: false,
      retryAfter: Math.ceil((hit.reset - now) / 1000),
      limit,
      remaining: 0,
      reset,
    };
  }

  hit.count += 1;
  return {
    allowed: true,
    retryAfter: 0,
    limit,
    remaining: limit - hit.count,
    reset,
  };
}

// ----------------------------------------------------------------------------
// 6. IDEMPOTENCY KEY ENGINE
// ----------------------------------------------------------------------------

const seenKeys = new Map<string, number>();
const IDEM_KEY_RE = /^[A-Za-z0-9-]{8,64}$/;
const IDEM_MAX_KEYS = 2000;

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

export function forgetKey(key: string | null) {
  if (key) seenKeys.delete(key);
}

// ----------------------------------------------------------------------------
// 7. SECURE PAYLOAD STREAM READER & PARSER
// ----------------------------------------------------------------------------

export async function readJsonCapped(req: Request, max: number): Promise<unknown> {
  const len = Number(req.headers.get("content-length") ?? 0);
  if (len > max) return undefined;

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
    "127.0.0.1"
  );
}

export function isSameOrigin(req: Request, siteUrl: string): boolean {
  const origin = req.headers.get("origin");
  const referer = req.headers.get("referer");
  if (!origin && !referer) return true; // CLI/curl: rate limit protects endpoint
  try {
    const allowed = new Set([new URL(siteUrl).origin, new URL(req.url).origin]);
    return allowed.has(new URL(origin ?? referer ?? "").origin);
  } catch {
    return false;
  }
}

export function corsHeaders(origin: string | null, siteUrl: string): HeadersInit {
  try {
    const site = new URL(siteUrl).origin;
    if (origin && new URL(origin).origin === site) {
      return {
        "Access-Control-Allow-Origin": site,
        Vary: "Origin",
      };
    }
  } catch {
    /* fall through */
  }
  return { Vary: "Origin" };
}

// ----------------------------------------------------------------------------
// 8. FILE UPLOAD HARDENING (MAGIC BYTES VALIDATION & MALWARE MITIGATION)
// ----------------------------------------------------------------------------

const ALLOWED_MIME_TYPES = new Set([
  "image/png",
  "image/jpeg",
  "image/webp",
  "application/pdf",
]);

const DANGEROUS_EXTENSIONS = new Set([
  "svg",
  "html",
  "htm",
  "js",
  "mjs",
  "exe",
  "sh",
  "bat",
  "cmd",
  "php",
  "phtml",
  "py",
  "jar",
  "vbs",
]);

/**
 * Validates upload buffer against file magic bytes to verify MIME type authenticity.
 * Completely blocks SVGs (stored XSS vector) and executable formats.
 */
export function validateUploadBuffer(file: {
  buffer: Uint8Array;
  name: string;
  mimeType: string;
  size: number;
}): { ok: boolean; error?: string; safeName?: string } {
  if (file.size <= 0 || file.size > 5 * 1024 * 1024) {
    return { ok: false, error: "File size must be between 1 byte and 5 MB." };
  }

  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  if (DANGEROUS_EXTENSIONS.has(ext)) {
    return { ok: false, error: "Disallowed file extension (executable or script risk)." };
  }

  if (!ALLOWED_MIME_TYPES.has(file.mimeType)) {
    return { ok: false, error: "Disallowed MIME type." };
  }

  const bytes = file.buffer;
  if (bytes.length < 8) {
    return { ok: false, error: "Corrupted or truncated file buffer." };
  }

  // 1. PNG Magic Bytes: 89 50 4E 47 0D 0A 1A 0A
  const isPng =
    bytes[0] === 0x89 &&
    bytes[1] === 0x50 &&
    bytes[2] === 0x4e &&
    bytes[3] === 0x47 &&
    bytes[4] === 0x0d &&
    bytes[5] === 0x0a &&
    bytes[6] === 0x1a &&
    bytes[7] === 0x0a;

  // 2. JPEG Magic Bytes: FF D8 FF
  const isJpeg = bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff;

  // 3. WebP Magic Bytes: 'RIFF'....'WEBP'
  const isWebp =
    bytes[0] === 0x52 &&
    bytes[1] === 0x49 &&
    bytes[2] === 0x46 &&
    bytes[3] === 0x46 &&
    bytes[8] === 0x57 &&
    bytes[9] === 0x45 &&
    bytes[10] === 0x42 &&
    bytes[11] === 0x50;

  // 4. PDF Magic Bytes: '%PDF' (25 50 44 46)
  const isPdf =
    bytes[0] === 0x25 &&
    bytes[1] === 0x50 &&
    bytes[2] === 0x44 &&
    bytes[3] === 0x46;

  let verifiedMime = "";
  if (isPng) verifiedMime = "image/png";
  else if (isJpeg) verifiedMime = "image/jpeg";
  else if (isWebp) verifiedMime = "image/webp";
  else if (isPdf) verifiedMime = "application/pdf";

  if (!verifiedMime || verifiedMime !== file.mimeType) {
    return { ok: false, error: "File content magic bytes do not match declared MIME type." };
  }

  // Generate non-colliding UUID filename
  const safeUuid = crypto.randomUUID();
  const safeName = `${safeUuid}.${ext}`;

  return { ok: true, safeName };
}

// ----------------------------------------------------------------------------
// 9. AUDITING, REDACTION & PRIVACY ERASURE (GDPR / PRIVACY ACT)
// ----------------------------------------------------------------------------

export function logSecurityEvent(event: string, fields: Record<string, unknown>) {
  const safe: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(fields)) {
    if (["name", "email", "message", "body", "password", "token"].includes(k)) {
      safe[k] = "[redacted]";
    } else {
      safe[k] = v;
    }
  }
  console.log(JSON.stringify({ event, timestamp: new Date().toISOString(), ...safe }));
}

/**
 * Permanently anonymizes personal identifiers for GDPR / Right to Be Forgotten.
 */
export function anonymizePersonalData(record: Record<string, unknown>): Record<string, unknown> {
  const scrubbed = { ...record };
  if ("name" in scrubbed) scrubbed.name = "Anonymized User";
  if ("email" in scrubbed) scrubbed.email = "anonymized@example.invalid";
  if ("message" in scrubbed) scrubbed.message = "[Content scrubbed per privacy request]";
  if ("ip" in scrubbed) scrubbed.ip = "0.0.0.0";
  scrubbed.anonymizedAt = new Date().toISOString();
  return scrubbed;
}
