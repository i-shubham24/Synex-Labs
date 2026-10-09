"use client";

import { motion, useMotionValue, useSpring } from "motion/react";
import { useEffect, useState } from "react";

// A small square that trails the pointer and names what you are about to open.
export function Cursor() {
  const x = useMotionValue(-100);
  const y = useMotionValue(-100);
  const sx = useSpring(x, { stiffness: 420, damping: 38, mass: 0.6 });
  const sy = useSpring(y, { stiffness: 420, damping: 38, mass: 0.6 });
  const [label, setLabel] = useState<string | null>(null);
  const [link, setLink] = useState(false);
  const [on, setOn] = useState(false);

  useEffect(() => {
    if (!matchMedia("(pointer: fine)").matches) return;
    // Pointer events can fire faster than frames. Stash the latest event and
    // process it once per frame, so DOM traversal + setState happen at most
    // ~60x/s instead of per event. Functional updates with a prev-check mean
    // React skips the re-render when nothing actually changed.
    let frame = 0;
    let pending: PointerEvent | null = null;
    const process = () => {
      frame = 0;
      if (!pending) return;
      const e = pending;
      pending = null;
      x.set(e.clientX);
      y.set(e.clientY);
      setOn(true);
      const target = e.target as Element | null;
      const tagged = target?.closest<HTMLElement>("[data-cursor]");
      const nextLabel = tagged?.dataset.cursor ?? null;
      const nextLink =
        !tagged && !!target?.closest("a,button,[role='button']");
      setLabel((prev) => (prev === nextLabel ? prev : nextLabel));
      setLink((prev) => (prev === nextLink ? prev : nextLink));
    };
    const move = (e: PointerEvent) => {
      pending = e;
      if (!frame) frame = requestAnimationFrame(process);
    };
    const leave = () => setOn(false);
    window.addEventListener("pointermove", move, { passive: true });
    document.documentElement.addEventListener("pointerleave", leave);
    return () => {
      if (frame) cancelAnimationFrame(frame);
      window.removeEventListener("pointermove", move);
      document.documentElement.removeEventListener("pointerleave", leave);
    };
  }, [x, y]);

  return (
    <motion.div
      aria-hidden
      className="pointer-events-none fixed top-0 left-0 z-[70] hidden md:block"
      style={{ x: sx, y: sy }}
    >
      <motion.div
        className="flex h-7 items-center justify-center overflow-hidden bg-signal text-[#11110f]"
        style={{ x: 14, y: 14, originX: 0, originY: 0 }}
        animate={{
          opacity: on ? 1 : 0,
          width: label ? "auto" : 10,
          height: label ? 28 : 10,
          rotate: link ? 45 : 0,
          scale: link ? 1.6 : 1,
        }}
        transition={{ type: "spring", stiffness: 380, damping: 30 }}
      >
        {label && (
          <span className="label px-2.5 whitespace-nowrap">{label}</span>
        )}
      </motion.div>
    </motion.div>
  );
}
