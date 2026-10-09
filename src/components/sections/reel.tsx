"use client";

import {
  motion,
  useAnimationFrame,
  useMotionValue,
  useReducedMotion,
  useScroll,
  useSpring,
  useTransform,
  useVelocity,
} from "motion/react";
import Image from "next/image";
import { useEffect, useRef } from "react";
import { cover, projects } from "@/data/projects";
import { useOpenProject } from "../project-dialog";

const wrap = (min: number, max: number, v: number) => {
  const range = max - min;
  return ((((v - min) % range) + range) % range) + min;
};

// A band of real screens that drifts sideways and speeds up with the scroll.
// It only does any work while it is on screen.
export function Reel() {
  const open = useOpenProject();
  const still = useReducedMotion();
  const section = useRef<HTMLElement>(null);
  const visible = useRef(true);
  const base = useMotionValue(0);
  const { scrollY } = useScroll();
  const velocity = useSpring(useVelocity(scrollY), {
    damping: 50,
    stiffness: 300,
  });
  const boost = useTransform(velocity, [-2000, 0, 2000], [-6, 0, 6]);
  const x = useTransform(base, (v) => `${wrap(-50, 0, v)}%`);
  const direction = useRef(-1);
  const paused = useRef(false);

  useEffect(() => {
    if (!section.current) return;
    const watch = new IntersectionObserver(([entry]) => {
      visible.current = entry.isIntersecting;
    });
    watch.observe(section.current);
    return () => watch.disconnect();
  }, []);

  useAnimationFrame((_, delta) => {
    if (still || paused.current || !visible.current) return;
    const b = boost.get();
    if (b < -0.2) direction.current = 1;
    else if (b > 0.2) direction.current = -1;
    base.set(
      base.get() + direction.current * 0.8 * (delta / 1000) * (1 + Math.abs(b)),
    );
  });

  return (
    <section
      ref={section}
      aria-label="Project screens"
      className="overflow-x-clip pt-10 pb-3 md:pt-16"
    >
      <motion.div
        className="flex w-max gap-3 pl-3 will-change-transform"
        style={{ x }}
        onPointerEnter={() => (paused.current = true)}
        onPointerLeave={() => (paused.current = false)}
      >
        {[0, 1].map((copy) =>
          projects.map((project, i) => (
            <button
              key={`${copy}-${project.slug}`}
              type="button"
              onClick={() => open(project.slug)}
              data-cursor="Open"
              aria-hidden={copy === 1}
              tabIndex={copy === 1 ? -1 : 0}
              aria-label={`View ${project.name}`}
              className="group w-[clamp(12rem,23vw,22rem)] shrink-0 overflow-hidden border border-border"
            >
              <Image
                src={cover(project)}
                alt=""
                width={1440}
                height={900}
                sizes="(max-width: 768px) 50vw, 23vw"
                priority={copy === 0 && i < 4}
                className="aspect-[16/10] w-full object-cover object-top transition-transform duration-700 ease-out-soft group-hover:scale-[1.04]"
              />
            </button>
          )),
        )}
      </motion.div>
    </section>
  );
}
