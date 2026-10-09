"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

// Letters swell toward the pointer using the font's width axis.
export function Kinetic({
  text,
  className,
  rest = 66,
  peak = 122,
  radius = 260,
}: {
  text: string;
  className?: string;
  rest?: number;
  peak?: number;
  radius?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    if (
      !matchMedia("(pointer: fine)").matches ||
      matchMedia("(prefers-reduced-motion: reduce)").matches
    )
      return;

    const letters = Array.from(root.querySelectorAll<HTMLElement>("[data-k]"));
    const level = letters.map(() => 0);
    const pointer = { x: -9999, y: -9999 };
    let frame = 0;

    const tick = () => {
      const centers = letters.map((el) => {
        const r = el.getBoundingClientRect();
        return [r.left + r.width / 2, r.top + r.height / 2];
      });
      let moving = false;
      letters.forEach((el, i) => {
        const d = Math.hypot(pointer.x - centers[i][0], pointer.y - centers[i][1]);
        const pull = Math.max(0, 1 - d / radius);
        const target = pull * pull;
        level[i] += (target - level[i]) * 0.16;
        if (Math.abs(target - level[i]) > 0.003) moving = true;
        el.style.fontStretch = `${rest + level[i] * (peak - rest)}%`;
      });
      frame = moving ? requestAnimationFrame(tick) : 0;
    };
    const onMove = (e: PointerEvent) => {
      pointer.x = e.clientX;
      pointer.y = e.clientY;
      if (!frame) frame = requestAnimationFrame(tick);
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      cancelAnimationFrame(frame);
    };
  }, [peak, radius, rest]);

  return (
    <span ref={ref} className={cn("inline-block whitespace-nowrap", className)}>
      <span className="sr-only">{text}</span>
      <span aria-hidden>
        {Array.from(text).map((ch, i) =>
          ch === " " ? (
            <span key={i}> </span>
          ) : (
            <span key={i} data-k className="inline-block">
              {ch}
            </span>
          ),
        )}
      </span>
    </span>
  );
}
