"use client";

import { useEffect, useState } from "react";
import { site } from "@/lib/site";
import { cn } from "@/lib/utils";
import { Cta } from "../cta";
import { EmailAddress } from "../email";
import { Fade, Rise } from "../reveal";

const NEEDS = ["Website", "Online store", "Web app", "AI tool", "Not sure yet"];
const FIELD =
  "w-full bg-[#11110f]/10 px-4 py-3.5 text-lg text-[#11110f] placeholder:text-[#11110f]/45 outline-none transition-colors focus:bg-[#11110f]/18";

function Clock() {
  const [time, setTime] = useState("");
  useEffect(() => {
    const format = () =>
      setTime(
        new Intl.DateTimeFormat("en-GB", {
          hour: "2-digit",
          minute: "2-digit",
          timeZone: site.timeZone,
        }).format(new Date()),
      );
    const first = setTimeout(format, 0);
    const loop = setInterval(format, 20000);
    return () => {
      clearTimeout(first);
      clearInterval(loop);
    };
  }, []);
  return <span className="tabular-nums">{time || "00:00"}</span>;
}

export function Contact() {
  const [need, setNeed] = useState(NEEDS[0]);
  const [status, setStatus] = useState<"idle" | "sending" | "done" | "error">("idle");
  const [error, setError] = useState("");

  // Posts to the same-origin /api/contact (validated + rate-limited server
  // side). Falls back to the visitor's mail app only if the API is unreachable.
  async function send(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);
    if (String(data.get("company") ?? "").trim() !== "") return; // honeypot
    const payload = {
      name: String(data.get("name") ?? ""),
      email: String(data.get("email") ?? ""),
      need,
      message: String(data.get("message") ?? ""),
    };
    setStatus("sending");
    setError("");
    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const json = (await res.json().catch(() => null)) as {
        ok?: boolean;
        error?: string;
        message?: string;
      } | null;
      if (res.ok && json?.ok) {
        setStatus("done");
        form.reset();
        return;
      }
      if (res.status === 429) {
        setError("Too many tries. Please wait a minute.");
      } else {
        setError(json?.error || "Could not send. Try the email link instead.");
      }
      setStatus("error");
    } catch {
      // Offline / API down: open the mail app with the brief filled in.
      const subject = `New project: ${need}`;
      const body = [
        `Name: ${payload.name}`,
        `Email: ${payload.email}`,
        `Looking for: ${need}`,
        "",
        payload.message,
      ].join("\n");
      window.location.href = `mailto:${site.email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
      setStatus("idle");
    }
  }

  return (
    <section id="contact" className="bg-signal py-24 text-[#11110f] md:py-36">
      <div className="shell grid grid-cols-12 gap-x-8 gap-y-14">
        <div className="col-span-12 flex flex-col justify-between gap-12 lg:col-span-6">
          <div className="flex flex-col gap-5">
            <p className="label flex gap-3">
              <span>08</span>
              <span>Contact</span>
            </p>
            <h2 className="display text-[clamp(3.2rem,9vw,9.5rem)]">
              <Rise>Got a project?</Rise>
              <Rise delay={0.08}>Tell us.</Rise>
            </h2>
          </div>

          <Fade className="flex flex-col gap-8">
            <EmailAddress className="wide w-fit text-[clamp(1rem,2.1vw,1.9rem)] break-all underline decoration-2 underline-offset-[0.3em] transition-[font-stretch] duration-500 ease-out-soft [font-stretch:100%] hover:[font-stretch:112%]" />
            <dl className="label grid max-w-md grid-cols-2 gap-y-2">
              <dt className="opacity-60">Based in</dt>
              <dd>{site.base}</dd>
              <dt className="opacity-60">Our time now</dt>
              <dd>
                <Clock /> IST
              </dd>
              <dt className="opacity-60">Reply</dt>
              <dd>Within a day</dd>
            </dl>
          </Fade>
        </div>

        <Fade className="col-span-12 lg:col-span-5 lg:col-start-8" delay={0.1}>
          <form onSubmit={send} className="flex flex-col gap-3" noValidate={false}>
            {/* Honeypot: hidden from humans, catches bots. */}
            <input
              type="text"
              name="company"
              autoComplete="off"
              tabIndex={-1}
              aria-hidden="true"
              className="absolute h-px w-px overflow-hidden opacity-0"
            />
            <label className="sr-only" htmlFor="name">
              Your name
            </label>
            <input
              id="name"
              name="name"
              required
              minLength={2}
              maxLength={100}
              autoComplete="name"
              placeholder="Your name"
              className={FIELD}
            />
            <label className="sr-only" htmlFor="email">
              Your email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              required
              maxLength={254}
              autoComplete="email"
              inputMode="email"
              placeholder="Your email"
              className={FIELD}
            />

            <fieldset className="py-3">
              <legend className="label mb-3">What do you need?</legend>
              <div className="flex flex-wrap gap-2">
                {NEEDS.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => setNeed(item)}
                    aria-pressed={need === item}
                    className={cn(
                      "px-4 py-2.5 font-semibold transition-colors duration-300",
                      need === item
                        ? "bg-[#11110f] text-[#efece4]"
                        : "bg-[#11110f]/10 hover:bg-[#11110f]/22",
                    )}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </fieldset>

            <label className="sr-only" htmlFor="message">
              About the project
            </label>
            <textarea
              id="message"
              name="message"
              required
              minLength={10}
              maxLength={2000}
              rows={5}
              placeholder="A few lines about the project"
              className={cn(FIELD, "resize-none")}
            />
            <Cta type="submit" tone="ink" size="lg" className="mt-2 w-full">
              {status === "sending" ? "Sending…" : "Send the brief"}
            </Cta>
            <p aria-live="polite" className="label min-h-5 text-[#11110f]/70">
              {status === "done"
                ? "Brief received. We reply within a day."
                : status === "error"
                  ? error
                  : ""}
            </p>
          </form>
        </Fade>
      </div>
    </section>
  );
}
