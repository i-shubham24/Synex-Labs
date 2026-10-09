"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

const COUNT = 760;
const GOLDEN = Math.PI * (3 - Math.sqrt(5));

function readColor(name: string) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// A disc of small boxes laid out like sunflower seeds. Rings of size and colour
// ripple outwards, and the boxes near the pointer swell. Plain 2D canvas, drawn
// only while it is on screen.
export function BoxField({ className }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    let size = 0;
    let dpr = 1;
    let ink = readColor("--foreground");
    let accent = readColor("--signal");
    const pointer = { x: -9, y: -9 };
    const still = matchMedia("(prefers-reduced-motion: reduce)").matches;

    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      size = canvas.clientWidth;
      canvas.width = canvas.height = Math.round(size * dpr);
    };
    const sizeWatch = new ResizeObserver(resize);
    sizeWatch.observe(canvas);
    resize();

    const themeWatch = new MutationObserver(() => {
      ink = readColor("--foreground");
      accent = readColor("--signal");
    });
    themeWatch.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });

    const onMove = (e: PointerEvent) => {
      const r = canvas.getBoundingClientRect();
      pointer.x = ((e.clientX - r.left) / r.width) * 2 - 1;
      pointer.y = ((e.clientY - r.top) / r.height) * 2 - 1;
    };
    window.addEventListener("pointermove", onMove, { passive: true });

    let visible = true;
    const viewWatch = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
    });
    viewWatch.observe(canvas);

    let frame = 0;
    // Thirty frames a second is plenty for a slow ripple.
    let skip = false;
    const draw = (now: number) => {
      frame = requestAnimationFrame(draw);
      skip = !skip;
      if (skip) return;
      if (!visible || document.hidden || size === 0) return;
      const t = still ? 0 : now / 1000;
      const half = (size * dpr) / 2;
      const radius = half * 0.96;
      const unit = (size * dpr) / 150;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      for (let k = 0; k < COUNT; k++) {
        const d = Math.sqrt((k + 0.5) / COUNT);
        const angle = k * GOLDEN + t * 0.04;
        const x = Math.cos(angle) * d;
        const y = Math.sin(angle) * d;
        // Two travelling ripples plus a soft edge.
        const wave = 0.5 + 0.5 * Math.sin(d * 13 - t * 1.6 + Math.sin(angle * 3 + t * 0.4));
        const near = Math.max(0, 1 - Math.hypot(x - pointer.x, y - pointer.y) / 0.42);
        const edge = Math.min(1, (1 - d) * 3.2);
        const s = unit * (0.45 + wave * 0.95 + near * 2.4) * (0.55 + edge * 0.45);
        const hot = wave > 0.72 || near > 0.25;
        ctx.globalAlpha = Math.min(1, (0.14 + wave * 0.55 + near) * (0.25 + edge * 0.75));
        ctx.fillStyle = hot ? accent : ink;
        ctx.fillRect(half + x * radius - s / 2, half + y * radius - s / 2, s, s);
      }
      if (still) cancelAnimationFrame(frame);
    };
    frame = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("pointermove", onMove);
      sizeWatch.disconnect();
      themeWatch.disconnect();
      viewWatch.disconnect();
    };
  }, []);

  return (
    <canvas
      ref={ref}
      aria-hidden
      className={cn("aspect-square w-full", className)}
    />
  );
}
