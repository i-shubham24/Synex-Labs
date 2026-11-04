// Sends a contact brief to the studio inbox through Resend's HTTP API.
// Server only: the key never reaches the browser. With no key configured the
// caller tells the visitor's browser to fall back to their own mail app.
import type { ContactInput } from "./security";

export type Delivery = "sent" | "unconfigured" | "failed";

export async function sendBrief(brief: ContactInput): Promise<Delivery> {
  const key = process.env.RESEND_API_KEY;
  const to = process.env.CONTACT_TO_EMAIL;
  if (!key || !to) return "unconfigured";
  // onboarding@resend.dev works before a domain is verified, but only to the
  // Resend account's own address.
  const from = process.env.CONTACT_FROM_EMAIL || "Synex Labs <onboarding@resend.dev>";

  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${key}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from,
        to: [to],
        // Replying in the inbox goes straight to the visitor.
        reply_to: brief.email,
        subject: `New brief: ${brief.need} from ${brief.name}`,
        text: [
          `Name: ${brief.name}`,
          `Email: ${brief.email}`,
          `Looking for: ${brief.need}`,
          "",
          brief.message,
        ].join("\n"),
      }),
      // Shorter than the form's own 8 second limit, so the visitor never
      // falls back to mail while this request is still in flight.
      signal: AbortSignal.timeout(5000),
      cache: "no-store",
    });
    return res.ok ? "sent" : "failed";
  } catch {
    return "failed";
  }
}
