import { MessageCircle } from "lucide-react";
import { whatsappLink } from "@/lib/contact";

// Floating chat button, bottom right. Square, signal colour, slides in once the
// page has settled. Renders nothing when no WhatsApp number is configured.
export function WhatsAppButton() {
  const href = whatsappLink();
  if (!href) return null;
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Chat with Synex Labs on WhatsApp"
      className="wa-float group fixed right-4 bottom-4 z-40 inline-flex h-12 items-center gap-2.5 bg-signal px-3.5 font-semibold text-[#11110f] shadow-lg transition-transform duration-300 ease-swift hover:-translate-y-0.5 md:right-6 md:bottom-6 md:h-14 md:px-5"
    >
      <MessageCircle aria-hidden className="size-5 transition-transform duration-300 group-hover:-rotate-12" />
      <span className="hidden text-sm sm:inline">WhatsApp us</span>
    </a>
  );
}
