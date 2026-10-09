"use client";

import { useSyncExternalStore } from "react";
import { site } from "@/lib/site";
import { RollLink } from "./cta";

// The address is assembled in the browser after mount, so the static HTML
// source contains no `mailto:` and no address text for harvesters. The
// visible text swaps in on hydration (one frame); pre-hydration the links
// point at #contact so they still do something useful.
function useEmail() {
  const ready = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
  if (!ready) return null;
  const at = site.email.indexOf("@");
  const address = `${site.email.slice(0, at)}@${site.email.slice(at + 1)}`;
  return { address, href: `mailto:${address}` };
}

// Short label link ("Email" in the footer).
export function EmailLink({
  label,
  className,
}: {
  label: string;
  className?: string;
}) {
  const email = useEmail();
  return (
    <RollLink href={email?.href ?? "#contact"} className={className}>
      {label}
    </RollLink>
  );
}

// Full address display (the big link in the contact section).
export function EmailAddress({ className }: { className?: string }) {
  const email = useEmail();
  return (
    <a
      href={email?.href ?? "#contact"}
      data-cursor="Write"
      className={className}
    >
      {email?.address ?? "Write to us"}
    </a>
  );
}
