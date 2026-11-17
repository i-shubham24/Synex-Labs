// Quick ways to reach the studio. Read at build time (the site is a static export).
// NEXT_PUBLIC_WHATSAPP_NUMBER overrides the studio number below; the booking link is
// left out entirely when NEXT_PUBLIC_BOOKING_URL is not set.

const STUDIO_WHATSAPP = "917973373923"; // +91 79733 73923

const digits = (process.env.NEXT_PUBLIC_WHATSAPP_NUMBER || STUDIO_WHATSAPP).replace(/\D/g, "");

export const whatsappNumber = digits.length >= 10 ? digits : null;

export const bookingUrl = /^https:\/\//.test(process.env.NEXT_PUBLIC_BOOKING_URL ?? "")
  ? (process.env.NEXT_PUBLIC_BOOKING_URL as string)
  : null;

/** wa.me link that opens a chat with the message already typed, or null. */
export function whatsappLink(message = "Hi Synex Labs, I would like a website for my business.") {
  if (!whatsappNumber) return null;
  return `https://wa.me/${whatsappNumber}?text=${encodeURIComponent(message)}`;
}

/** Rupees with Indian digit grouping, e.g. 124999 -> "1,24,999". */
export function inr(amount: number) {
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(amount);
}
