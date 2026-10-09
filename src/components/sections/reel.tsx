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
import { useRef } from "react";
import { cover, projects } from "@/data/projects";
import { useOpenProject } from "../project-dialog";
import { Frame, Shot } from "../shot";

const wrap = (min: number, max: number, v: number) => {
  const range = max - min;
  return ((((v - min) % range) + range) % range) + min;
};

// A band of real screens that drifts sideways and speeds up with the scroll.
export function Reel() {
  const open = useOpenProject();
  const still = useReducedMotion();
  const base = useMotionValue(0);
  const { scrollY } = useScroll();
  const velocity = useSpring(useVelocity(scrollY), {
    damping: 50,
    stiffness: 300,
  });
  const boost = useTransform(velocity, [-2000, 0, 2000], [-6, 0, 6]);
  const skew = useTransform(velocity, [-2500, 2500], [4, -4]);
  const x = useTransform(base, (v) => `${wrap(-50, 0, v)}%`);
  const direction = useRef(-1);
  const paused = useRef(false);

  useAnimationFrame((_, delta) => {
    if (still || paused.current) return;
    const b = boost.get();
    if (b < -0.2) direction.current = 1;
    else if (b > 0.2) direction.current = -1;
    base.set(
      base.get() + direction.current * 0.8 * (delta / 1000) * (1 + Math.abs(b)),
    );
  });

  return (
    <section aria-label="Project screens" className="overflow-x-clip pt-4 pb-10">
      <motion.div
        className="flex w-max gap-5 pl-5"
        style={{ x, skewX: still ? 0 : skew }}
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
              className="group w-[clamp(17rem,34vw,32rem)] shrink-0 text-left"
            >
              <Frame url={project.url}>
                <Shot
                  frames={[cover(project)]}
                  alt={`${project.name} home page`}
                  sizes="(max-width: 768px) 72vw, 34vw"
                  priority={copy === 0 && i < 3}
                  className="transition-transform duration-700 ease-out-soft group-hover:scale-[1.03]"
                />
              </Frame>
              <span className="label mt-3 flex justify-between gap-4 text-muted-foreground">
                <span className="text-foreground">{project.name}</span>
                <span>{project.kind}</span>
              </span>
            </button>
          )),
        )}
      </motion.div>
    </section>
  );
}
