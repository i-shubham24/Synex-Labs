"use client";

import { AnimatePresence, motion, useInView } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { steps } from "@/data/content";
import { cn } from "@/lib/utils";
import { Label, Rise } from "../reveal";

const EASE = [0.7, 0, 0.2, 1] as const;

// One line diagram per step, part solid and part dotted, with small square
// handles. Each one draws itself when its step becomes active.
const ART = [
  // Talk: two sides inside one shared frame, with a message passing between them
  <svg key="talk" viewBox="0 0 520 160" className="draw size-full">
    <path d="M80 158a78 78 0 0 1 0-156h190" pathLength="1" />
    <path d="M440 2a78 78 0 0 1 0 156H330" pathLength="1" />
    <path className="dots" d="M270 2h170M330 158H80" />
    <circle cx="80" cy="80" r="52" pathLength="1" />
    <circle cx="440" cy="80" r="52" pathLength="1" />
    <rect className="fill" x="-5" y="-5" width="10" height="10">
      <animateMotion dur="2.6s" repeatCount="indefinite" path="M132 80H388" />
    </rect>
  </svg>,
  // Plan: a frame being shaped by its corner handles
  <svg key="plan" viewBox="0 0 520 160" className="draw size-full">
    <path d="M8 150 82 30 460 8 512 150Z" pathLength="1" />
    <path className="dots" d="M82 30 512 150M8 150 460 8" />
    <rect x="2" y="144" width="12" height="12" pathLength="1" />
    <rect x="76" y="24" width="12" height="12" pathLength="1" />
    <rect x="506" y="144" width="12" height="12" pathLength="1" />
    <rect className="fill" x="454" y="2" width="12" height="12" />
    <path className="fill" d="M470 18l5 26 7-10 12-3z" />
  </svg>,
  // Build: layers stacking up
  <svg key="build" viewBox="0 0 520 160" className="draw size-full">
    <path d="M40 46 260 6l220 40-220 40Z" pathLength="1" />
    <path d="M40 80l220 40 220-40" pathLength="1" />
    <path d="M40 114l220 40 220-40" pathLength="1" />
    <path className="dots" d="M40 46v68M480 46v68M260 86v68" />
    <rect className="fill" x="254" y="40" width="12" height="12" />
  </svg>,
  // Launch: lift-off, with support circling round it
  <svg key="launch" viewBox="0 0 520 160" className="draw size-full">
    <circle className="dots" cx="120" cy="80" r="74" />
    <circle cx="120" cy="80" r="34" pathLength="1" />
    <path d="M154 66 470 20" pathLength="1" />
    <path d="M440 8l32 11-18 28" pathLength="1" />
    <rect className="fill" x="188" y="74" width="12" height="12">
      <animateTransform
        attributeName="transform"
        type="rotate"
        from="0 120 80"
        to="360 120 80"
        dur="9s"
        repeatCount="indefinite"
      />
    </rect>
  </svg>,
];

// The heading and its diagram stay put on the left while the steps scroll by on
// the right. The big number sits between them and counts along.
export function Process() {
  const [active, setActive] = useState(0);

  return (
    <section id="process" className="pb-24 md:pb-36">
      <div className="shell">
        <Label index="05">Process</Label>

        <div className="mt-8 grid grid-cols-12 gap-x-8 md:mt-12">
          <div className="col-span-12 lg:col-span-7">
            <div className="lg:sticky lg:top-24">
              <div className="flex items-start justify-between gap-6">
                <h2 className="title text-[clamp(2.6rem,5.4vw,5.4rem)]">
                  <Rise>Four steps.</Rise>
                  <Rise delay={0.08}>
                    <i>No surprises.</i>
                  </Rise>
                </h2>
                <div
                  aria-hidden
                  className="display hidden h-[0.8em] shrink-0 overflow-hidden text-[clamp(7rem,13vw,13rem)] leading-[0.8] text-signal lg:block"
                >
                  <AnimatePresence mode="popLayout" initial={false}>
                    <motion.span
                      key={active}
                      className="block"
                      initial={{ y: "100%" }}
                      animate={{ y: "0%" }}
                      exit={{ y: "-100%" }}
                      transition={{ duration: 0.6, ease: EASE }}
                    >
                      0{active + 1}
                    </motion.span>
                  </AnimatePresence>
                </div>
              </div>

              <div className="relative mt-12 hidden h-[min(30svh,15rem)] max-w-[40rem] text-signal lg:block">
                {ART.map((art, i) => (
                  <div
                    key={i}
                    className={cn(
                      "absolute inset-0 transition-opacity duration-500",
                      active === i ? "is-on opacity-100" : "opacity-0",
                    )}
                  >
                    {art}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <ol className="relative col-span-12 mt-12 flex flex-col pl-8 md:pl-12 lg:col-span-4 lg:col-start-9 lg:mt-0 lg:py-[12svh]">
            <span
              aria-hidden
              className="absolute top-0 bottom-0 left-[3px] w-px bg-border"
            />
            {steps.map((step, i) => (
              <Step
                key={step.name}
                index={i}
                name={step.name}
                line={step.line}
                on={active === i}
                done={active >= i}
                onEnter={setActive}
              />
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}

function Step({
  index,
  name,
  line,
  on,
  done,
  onEnter,
}: {
  index: number;
  name: string;
  line: string;
  on: boolean;
  done: boolean;
  onEnter: (i: number) => void;
}) {
  const ref = useRef<HTMLLIElement>(null);
  const centered = useInView(ref, { margin: "-48% 0px -48% 0px" });

  useEffect(() => {
    if (centered) onEnter(index);
  }, [centered, index, onEnter]);

  return (
    <li
      ref={ref}
      className={cn(
        "is-on relative flex flex-col justify-center gap-4 py-8 transition-opacity duration-500 lg:min-h-[40svh] lg:py-0",
        on ? "opacity-100" : "lg:opacity-30",
      )}
    >
      <span
        aria-hidden
        className={cn(
          "absolute top-1/2 -left-8 size-[7px] -translate-y-1/2 transition-colors duration-500 md:-left-12",
          done ? "bg-signal" : "bg-muted-foreground",
        )}
      />
      <span
        className={cn(
          "label transition-colors duration-500",
          on ? "text-signal" : "text-muted-foreground",
        )}
      >
        Step 0{index + 1}
      </span>
      <h3 className="title text-[clamp(2.6rem,5vw,5rem)]">{name}</h3>
      <p className="max-w-md text-xl leading-snug text-pretty">{line}</p>
      <div className="mt-2 h-28 max-w-sm text-signal lg:hidden">
        {ART[index]}
      </div>
    </li>
  );
}
