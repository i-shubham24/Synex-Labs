"use client";

import { useEffect, useState } from "react";
import { site } from "@/lib/site";
import { cn } from "@/lib/utils";
import { Cta } from "../cta";
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

  // No server yet: the form opens the visitor's mail app with the brief filled in.
  function send(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const subject = `New project: ${need}`;
    const body = [
      `Name: ${data.get("name")}`,
      `Email: ${data.get("email")}`,
      `Looking for: ${need}`,
      "",
      `${data.get("message")}`,
    ].join("\n");
    window.location.href = `mailto:${site.email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
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
            <a
              href={`mailto:${site.email}`}
              data-cursor="Write"
              className="wide w-fit text-[clamp(1rem,2.1vw,1.9rem)] break-all underline decoration-2 underline-offset-[0.3em] transition-[font-stretch] duration-500 ease-out-soft [font-stretch:100%] hover:[font-stretch:112%]"
            >
              {site.email}
            </a>
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
          <form onSubmit={send} className="flex flex-col gap-3">
            <label className="sr-only" htmlFor="name">
              Your name
            </label>
            <input
              id="name"
              name="name"
              required
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
              autoComplete="email"
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
              rows={5}
              placeholder="A few lines about the project"
              className={cn(FIELD, "resize-none")}
            />
            <Cta type="submit" tone="ink" size="lg" className="mt-2 w-full">
              Send the brief
            </Cta>
          </form>
        </Fade>
      </div>
    </section>
  );
}
