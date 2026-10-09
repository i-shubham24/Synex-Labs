"use client";

import { motion } from "motion/react";
import { cn } from "@/lib/utils";

const EASE = [0.16, 1, 0.3, 1] as const;

// Slides a line of text up from behind its own baseline when it scrolls into view.
export function Rise({
  children,
  delay = 0,
  className,
  show,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
  // Pass a boolean to control it by hand instead of by scroll position.
  show?: boolean;
}) {
  const controlled = show !== undefined;
  return (
    <span
      className={cn(
        "block [clip-path:inset(-0.06em_-50vw_-0.18em_-2vw)]",
        className,
      )}
    >
      <motion.span
        className="block"
        initial={{ y: "118%" }}
        animate={controlled ? { y: show ? "0%" : "118%" } : undefined}
        whileInView={controlled ? undefined : { y: "0%" }}
        viewport={{ once: true, margin: "0px 0px -12% 0px" }}
        transition={{ duration: 0.95, ease: EASE, delay }}
      >
        {children}
      </motion.span>
    </span>
  );
}

// Fades a block up into place when it scrolls into view.
export function Fade({
  children,
  delay = 0,
  className,
  y = 28,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
  y?: number;
}) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "0px 0px -10% 0px" }}
      transition={{ duration: 0.8, ease: EASE, delay }}
    >
      {children}
    </motion.div>
  );
}

// Section label: index, a short rule, the name, then a hairline that draws across.
export function Label({
  index,
  children,
  className,
}: {
  index: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-4", className)}>
      <p className="label flex items-center gap-3">
        <span className="text-signal">{index}</span>
        <span aria-hidden className="h-px w-7 bg-current opacity-50" />
        <span>{children}</span>
      </p>
      <motion.span
        aria-hidden
        className="block h-px origin-left bg-foreground/30"
        initial={{ scaleX: 0 }}
        whileInView={{ scaleX: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 1.2, ease: [0.7, 0, 0.2, 1] }}
      />
    </div>
  );
}

// Section opener. Lines may hold <em> for the accent word and <i> for the quiet one.
export function SectionHead({
  index,
  label,
  title,
  aside,
  className,
}: {
  index: string;
  label: string;
  title: React.ReactNode[];
  aside?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-8 md:gap-12", className)}>
      <Label index={index}>{label}</Label>
      <div className="grid grid-cols-12 items-end gap-x-8 gap-y-6">
        <h2 className="title col-span-12 text-[clamp(2.6rem,6.3vw,6.4rem)] lg:col-span-8">
          {title.map((line, i) => (
            <Rise key={i} delay={i * 0.08}>
              {line}
            </Rise>
          ))}
        </h2>
        {aside && (
          <Fade className="col-span-12 lg:col-span-4" delay={0.15}>
            <p className="max-w-md text-lg leading-snug text-pretty">{aside}</p>
          </Fade>
        )}
      </div>
    </div>
  );
}
