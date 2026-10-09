"use client";

import { motion, useScroll, useTransform } from "motion/react";
import { useRef } from "react";
import { Cta } from "../cta";
import { useIntroDone } from "../intro";
import { Kinetic } from "../kinetic";
import { LiquidMark } from "../liquid-mark";
import { Rise } from "../reveal";

const LINES = [
  { text: "Websites", accent: false },
  { text: "that win you", accent: false },
  { text: "clients.", accent: true },
];
const EASE = [0.16, 1, 0.3, 1] as const;

export function Hero() {
  const ref = useRef<HTMLElement>(null);
  const ready = useIntroDone();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });
  const drift = [
    useTransform(scrollYProgress, [0, 1], ["0%", "-9%"]),
    useTransform(scrollYProgress, [0, 1], ["0%", "7%"]),
    useTransform(scrollYProgress, [0, 1], ["0%", "-5%"]),
  ];
  const markY = useTransform(scrollYProgress, [0, 1], ["0%", "22%"]);
  const markRotate = useTransform(scrollYProgress, [0, 1], [0, 14]);

  return (
    <section
      id="top"
      ref={ref}
      className="relative flex min-h-[88svh] flex-col overflow-x-clip pt-16 md:pt-[4.5rem]"
    >
      <div className="shell flex flex-1 flex-col">
        <motion.div
          className="label flex items-center justify-between gap-4 border-t border-border py-3 text-muted-foreground"
          initial={{ opacity: 0 }}
          animate={ready ? { opacity: 1 } : undefined}
          transition={{ duration: 0.8, delay: 0.5 }}
        >
          <span>Web studio / India</span>
          <span className="flex items-center gap-2 text-foreground">
            <span className="size-2 animate-pulse bg-signal" />
            Taking new projects
          </span>
        </motion.div>

        <div className="corners flex flex-1 flex-col justify-between gap-10 px-3 py-6 md:px-5 md:py-8">
          <div className="grid grid-cols-12 items-center gap-x-6 gap-y-2">
            <h1 className="display order-2 col-span-12 text-[clamp(3.5rem,15.4vw,8rem)] lg:order-1 lg:col-span-8 lg:text-[clamp(6rem,10.6vw,12.5rem)]">
              {LINES.map((line, i) => (
                <Rise key={line.text} show={ready} delay={0.1 + i * 0.09}>
                  <motion.span className="block" style={{ x: drift[i] }}>
                    <Kinetic
                      text={line.text}
                      className={line.accent ? "text-signal" : undefined}
                    />
                  </motion.span>
                </Rise>
              ))}
            </h1>

            <motion.div
              className="order-1 col-span-12 lg:order-2 lg:col-span-4"
              style={{ y: markY, rotate: markRotate }}
              initial={{ opacity: 0, scale: 0.86 }}
              animate={ready ? { opacity: 1, scale: 1 } : undefined}
              transition={{ duration: 1.1, ease: EASE, delay: 0.25 }}
            >
              <LiquidMark className="-my-[6%] ml-[-9%] w-[62vw] max-w-[22rem] lg:my-[-12%] lg:mr-[-10%] lg:ml-[-12%] lg:w-[122%] lg:max-w-none" />
            </motion.div>
          </div>

          <motion.div
            className="grid grid-cols-12 items-end gap-x-6 gap-y-7"
            initial={{ opacity: 0, y: 24 }}
            animate={ready ? { opacity: 1, y: 0 } : undefined}
            transition={{ duration: 0.9, ease: EASE, delay: 0.55 }}
          >
            <p className="col-span-12 max-w-[34rem] text-lg leading-snug text-pretty md:col-span-6 md:text-xl lg:col-span-5">
              Synex Labs is a two person studio. We design and build websites,
              online stores, web apps and AI tools for businesses in India,
              Switzerland and Australia.
            </p>
            <div className="col-span-12 flex flex-wrap items-center gap-3 md:col-span-6 md:justify-end lg:col-span-7">
              <Cta href="#contact" tone="signal" size="lg" className="min-w-52">
                Start a project
              </Cta>
              <Cta href="#work" size="lg" className="min-w-44">
                See our work
              </Cta>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
