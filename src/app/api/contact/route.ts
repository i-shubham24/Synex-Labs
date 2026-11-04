import { NextResponse } from "next/server";
import { sendBrief } from "@/lib/mail";
import {
  clientIp,
  corsHeaders,
  firstTime,
  forgetKey,
  isSameOrigin,
  logContactEvent,
  rateLimit,
  readJsonCapped,
  validateContact,
  type RateLimitInfo,
} from "@/lib/security";
import { site } from "@/lib/site";

function noStore(res: NextResponse) {
  res.headers.set("Cache-Control", "no-store");
  return res;
}

/** Standard rate limit headers for every response of this endpoint. */
function rateHeaders(rl: RateLimitInfo): Record<string, string> {
  return {
    "X-RateLimit-Limit": String(rl.limit),
    "X-RateLimit-Remaining": String(rl.remaining),
    "X-RateLimit-Reset": String(rl.reset),
  };
}

export async function OPTIONS(req: Request) {
  const res = new NextResponse(null, { status: 204 });
  for (const [k, v] of Object.entries(
    corsHeaders(req.headers.get("origin"), site.url),
  ))
    res.headers.set(k, v as string);
  res.headers.set("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.headers.set("Access-Control-Allow-Headers", "Content-Type, Idempotency-Key");
  res.headers.set("Access-Control-Max-Age", "600");
  return res;
}

export async function POST(req: Request) {
  const cors = corsHeaders(req.headers.get("origin"), site.url);

  // CSRF: only accept same-origin form posts.
  if (!isSameOrigin(req, site.url)) {
    logContactEvent("contact.forbidden", { reason: "origin" });
    return noStore(
      NextResponse.json({ ok: false, error: "Forbidden." }, { status: 403, headers: cors }),
    );
  }

  // Rate limit: 5 briefs / minute / IP.
  const ip = clientIp(req.headers);
  const rl = await rateLimit(`contact:${ip}`, 5, 60_000);
  const headers = { ...cors, ...rateHeaders(rl) } as Record<string, string>;
  if (!rl.allowed) {
    const res = NextResponse.json(
      { ok: false, error: "Too many tries. Wait a minute." },
      { status: 429, headers },
    );
    res.headers.set("Retry-After", String(rl.retryAfter));
    return noStore(res);
  }

  // The longest valid brief is about 2.5 KB of text, so 16 KB is plenty.
  let body: unknown;
  try {
    body = await readJsonCapped(req, 16 * 1024);
  } catch {
    return noStore(
      NextResponse.json({ ok: false, error: "Invalid payload." }, { status: 400, headers }),
    );
  }
  if (body === undefined)
    return noStore(
      NextResponse.json({ ok: false, error: "Message too long." }, { status: 413, headers }),
    );

  const checked = validateContact(body);
  if (!checked.ok)
    return noStore(
      NextResponse.json({ ok: false, error: checked.error }, { status: 400, headers }),
    );
  if (checked.data?.company === "bot") {
    // Honeypot hit: pretend it worked.
    return noStore(NextResponse.json({ ok: true }, { headers }));
  }

  // Idempotency: a retried / double-clicked submit replays the first answer.
  const idemKey = req.headers.get("idempotency-key");
  if (!firstTime(idemKey)) {
    logContactEvent("contact.replay", { need: checked.data?.need });
    return noStore(
      NextResponse.json(
        { ok: true, message: "Brief already received. We reply within a day." },
        { headers: { ...headers, "X-Idempotent-Replay": "true" } },
      ),
    );
  }

  const delivery = await sendBrief(checked.data!);
  logContactEvent(`contact.${delivery}`, { need: checked.data?.need });
  if (delivery !== "sent") {
    // Nothing reached the inbox. Let a retry through, and have the browser
    // hand the brief to the visitor's own mail app so it is not lost.
    forgetKey(idemKey);
    return noStore(
      NextResponse.json(
        { ok: false, fallback: "mail", error: "Opening your mail app instead." },
        { status: 503, headers },
      ),
    );
  }

  return noStore(
    NextResponse.json(
      { ok: true, message: "Brief received. We reply within a day." },
      { headers },
    ),
  );
}
