import { NextResponse } from "next/server";
import {
  clientIp,
  corsHeaders,
  isSameOrigin,
  logContactEvent,
  rateLimit,
  validateContact,
} from "@/lib/security";
import { site } from "@/lib/site";

function noStore(res: NextResponse) {
  res.headers.set("Cache-Control", "no-store");
  return res;
}

export async function OPTIONS(req: Request) {
  const res = new NextResponse(null, { status: 204 });
  for (const [k, v] of Object.entries(
    corsHeaders(req.headers.get("origin"), site.url),
  ))
    res.headers.set(k, v as string);
  res.headers.set("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.headers.set("Access-Control-Allow-Headers", "Content-Type");
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
  const rl = rateLimit(`contact:${ip}`, 5, 60_000);
  if (!rl.allowed) {
    const res = NextResponse.json(
      { ok: false, error: "Too many tries. Wait a minute." },
      { status: 429, headers: cors },
    );
    res.headers.set("Retry-After", String(rl.retryAfter));
    return noStore(res);
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return noStore(
      NextResponse.json({ ok: false, error: "Invalid payload." }, { status: 400, headers: cors }),
    );
  }

  const checked = validateContact(body);
  if (!checked.ok)
    return noStore(
      NextResponse.json({ ok: false, error: checked.error }, { status: 400, headers: cors }),
    );
  if (checked.data?.company === "bot") {
    // Honeypot hit: pretend it worked.
    return noStore(NextResponse.json({ ok: true }, { headers: cors }));
  }

  // No mail provider is wired yet: log metadata only (PII redacted).
  logContactEvent("contact.received", { need: checked.data?.need });

  return noStore(
    NextResponse.json(
      { ok: true, message: "Brief received. We reply within a day." },
      { headers: cors },
    ),
  );
}
