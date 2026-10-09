"use client";

import {
  AnimatePresence,
  motion,
  useInView,
  useScroll,
  useSpring,
} from "motion/react";
import { useEffect, useRef, useState } from "react";
import { steps } from "@/data/content";
import { cn } from "@/lib/utils";
import { Label, Rise } from "../reveal";

const EASE = [0.7, 0, 0.2, 1] as const;

export function Process() {
  const [active, setActive] = useState(0);
  const list = useRef<HTMLOListElement>(null);
  const { scrollYProgress } = useScroll({
    target: list,
    offset: ["start 60%", "end 60%"],
  });
  const fill = useSpring(scrollYProgress, { stiffness: 120, damping: 28 });

  return (
    <section id="process" className="pb-24 md:pb-36">
      <div className="shell">
        <Label index="04">Process</Label>

        <div className="mt-8 grid grid-cols-12 gap-x-8 md:mt-12">
          <div className="col-span-12 lg:col-span-6">
            <div className="lg:sticky lg:top-28">
              <h2 className="title text-[clamp(2.6rem,6.3vw,6.4rem)]">
                <Rise>Four steps.</Rise>
                <Rise delay={0.08}>
                  <i>No surprises.</i>
                </Rise>
              </h2>
              <div
                aria-hidden
                className="display mt-10 hidden h-[0.8em] overflow-hidden text-[clamp(10rem,20vw,20rem)] leading-[0.8] text-signal lg:block"
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
          </div>

          <ol
            ref={list}
            className="relative col-span-12 mt-12 flex flex-col pl-8 md:pl-12 lg:col-span-5 lg:col-start-8 lg:mt-0 lg:py-[10svh]"
          >
            <span
              aria-hidden
              className="absolute top-0 bottom-0 left-[3px] w-px bg-border"
            />
            <motion.span
              aria-hidden
              className="absolute top-0 bottom-0 left-[3px] w-px origin-top bg-signal"
              style={{ scaleY: fill }}
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
      className="relative flex flex-col justify-center gap-4 py-8 lg:min-h-[36svh] lg:py-0"
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
      <h3
        className={cn(
          "title text-[clamp(2.6rem,5.6vw,5.6rem)] transition-colors duration-500",
          on ? "text-foreground" : "lg:text-foreground/30",
        )}
      >
        {name}
      </h3>
      <p
        className={cn(
          "max-w-md text-xl leading-snug text-pretty transition-opacity duration-500",
          on ? "opacity-100" : "lg:opacity-40",
        )}
      >
        {line}
      </p>
    </li>
  );
}
