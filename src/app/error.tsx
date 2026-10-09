"use client";

import { useEffect } from "react";
import { Cta } from "@/components/cta";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log only the digest/message — never user data or component stacks
    // containing form input.
    console.error(JSON.stringify({ event: "page.error", digest: error.digest ?? null }));
  }, [error]);

  return (
    <main className="shell flex min-h-[80svh] flex-col items-start justify-center gap-6 pt-16">
      <p className="label flex items-center gap-2.5">
        <span aria-hidden className="size-1.5 bg-signal" />
        <span className="text-signal">Error</span>
        <span>Something broke</span>
      </p>
      <h1 className="title text-[clamp(2.6rem,7vw,6rem)]">
        That <i>did not work.</i>
      </h1>
      <p className="max-w-md text-lg leading-snug text-pretty text-muted-foreground">
        Give it another go. If it keeps failing, reach us directly by email —
        a human replies within a day.
      </p>
      <div className="flex flex-wrap gap-3">
        <Cta tone="signal" size="lg" className="min-w-44" onClick={reset}>
          Try again
        </Cta>
        <Cta href="/" size="lg" className="min-w-44">
          Back to home
        </Cta>
      </div>
    </main>
  );
}
