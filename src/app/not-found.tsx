import type { Metadata } from "next";
import { Cta } from "@/components/cta";

export const metadata: Metadata = {
  title: "Page not found",
  description: "This page does not exist. Head back to Synex Labs.",
  robots: { index: false, follow: false },
};

export default function NotFound() {
  return (
    <main className="shell flex min-h-[80svh] flex-col items-start justify-center gap-6 pt-16">
      <p className="label flex items-center gap-2.5">
        <span aria-hidden className="size-1.5 bg-signal" />
        <span className="text-signal">404</span>
        <span>Not found</span>
      </p>
      <h1 className="title text-[clamp(2.6rem,7vw,6rem)]">
        Nothing here <i>but pixels.</i>
      </h1>
      <p className="max-w-md text-lg leading-snug text-pretty text-muted-foreground">
        The page you asked for moved or never existed. The work, the team and
        the contact form are all one click away.
      </p>
      <Cta href="/" tone="signal" size="lg" className="min-w-52">
        Back to home
      </Cta>
    </main>
  );
}
