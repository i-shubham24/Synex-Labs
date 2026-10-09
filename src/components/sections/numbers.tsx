"use client";

import {
  animate,
  motion,
  useInView,
  useMotionValue,
  useTransform,
} from "motion/react";
import { useEffect, useRef } from "react";
import { numbers, reasons } from "@/data/content";
import { Cta } from "../cta";
import { Fade, SectionHead } from "../reveal";

const LETTERS = ["A", "B", "C"];

function Count({ to }: { to: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const seen = useInView(ref, { once: true, margin: "0px 0px -15% 0px" });
  const value = useMotionValue(0);
  const text = useTransform(value, (v) => String(Math.round(v)).padStart(2, "0"));

  useEffect(() => {
    if (!seen) return;
    const run = animate(value, to, { duration: 1.6, ease: [0.16, 1, 0.3, 1] });
    return () => run.stop();
  }, [seen, to, value]);

  return (
    <span ref={ref}>
      <span className="sr-only">{to}</span>
      <motion.span aria-hidden>{text}</motion.span>
    </span>
  );
}

// A ruled grid: three facts on top, three reasons below.
export function Numbers() {
  return (
    <section id="why" className="py-24 md:py-36">
      <div className="shell">
        <SectionHead
          index="03"
          label="Why us"
          title={[
            <>Small team.</>,
            <>
              <em>Straight answers.</em>
            </>,
          ]}
        />

        <Fade className="mt-14 md:mt-20">
          <div className="grid border-t border-l border-border md:grid-cols-3">
            {numbers.map((item) => (
              <div
                key={item.label}
                className="flex flex-col justify-between gap-10 border-r border-b border-border p-6 md:p-9"
              >
                <p className="label text-muted-foreground">{item.label}</p>
                <p className="display text-[clamp(6rem,13vw,13rem)] leading-[0.8] tabular-nums">
                  <Count to={item.value} />
                </p>
              </div>
            ))}

            {reasons.map((item, i) => (
              <div
                key={item.name}
                className="group flex flex-col gap-10 border-r border-b border-border p-6 transition-colors duration-500 hover:bg-card md:p-9"
              >
                <span className="label grid size-8 place-items-center border border-signal text-signal transition-colors duration-300 group-hover:bg-signal group-hover:text-[#11110f]">
                  {LETTERS[i]}
                </span>
                <div className="flex flex-col gap-3">
                  <h3 className="title text-2xl md:text-[1.75rem]">
                    {item.name}
                  </h3>
                  <p className="max-w-sm leading-snug text-pretty text-muted-foreground">
                    {item.line}
                  </p>
                </div>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-5 border-x border-b border-border p-6 md:p-9">
            <p className="title text-2xl md:text-3xl">
              Have something in mind? <i>Let us take a look.</i>
            </p>
            <Cta href="#contact" tone="signal" size="lg" className="min-w-52">
              Start a project
            </Cta>
          </div>
        </Fade>
      </div>
    </section>
  );
}
