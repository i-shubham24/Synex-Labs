"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const DOTS = ["bg-signal", "bg-acid", "bg-tide"];

// A window frame around a screenshot, so it reads as a real site and not a mockup.
export function Frame({
  url,
  children,
  className,
}: {
  url?: string;
  children: React.ReactNode;
  className?: string;
}) {
  const host = url?.replace(/^https?:\/\//, "").replace(/\/$/, "");
  return (
    <div className={cn("overflow-hidden bg-card", className)}>
      <div className="flex h-7 items-center gap-1.5 px-3">
        {DOTS.map((c) => (
          <span key={c} className={cn("size-1.5", c)} />
        ))}
        {host && (
          <span className="label ml-2 truncate text-[0.62rem] text-muted-foreground normal-case">
            {host}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

// Shows the first frame. While `play` is on it steps through the rest.
export function Shot({
  frames,
  alt,
  play = false,
  sizes,
  priority = false,
  className,
}: {
  frames: string[];
  alt: string;
  play?: boolean;
  sizes: string;
  priority?: boolean;
  className?: string;
}) {
  const [index, setIndex] = useState(0);
  const [armed, setArmed] = useState(false);

  useEffect(() => {
    if (!play || frames.length < 2) return;
    const first = setTimeout(() => {
      setArmed(true);
      setIndex(1);
    }, 0);
    const loop = setInterval(
      () => setIndex((i) => (i + 1) % frames.length),
      1300,
    );
    return () => {
      clearTimeout(first);
      clearInterval(loop);
      setIndex(0);
    };
  }, [play, frames.length]);

  return (
    <div className={cn("relative aspect-[16/10] overflow-hidden", className)}>
      {(armed ? frames : frames.slice(0, 1)).map((src, i) => (
        <Image
          key={src}
          src={src}
          alt={i === 0 ? alt : ""}
          width={1440}
          height={900}
          sizes={sizes}
          priority={priority && i === 0}
          className={cn(
            "absolute inset-0 size-full object-cover object-top transition-opacity duration-500",
            i === index ? "opacity-100" : "opacity-0",
          )}
        />
      ))}
      {frames.length > 1 && (
        <div
          aria-hidden
          className={cn(
            "absolute right-3 bottom-3 flex gap-1 transition-opacity duration-300",
            play ? "opacity-100" : "opacity-0",
          )}
        >
          {frames.map((src, i) => (
            <span
              key={src}
              className={cn(
                "size-1.5 transition-colors",
                i === index ? "bg-signal" : "bg-white/60",
              )}
            />
          ))}
        </div>
      )}
    </div>
  );
}

const STATUS = {
  Live: "bg-tide",
  "In build": "bg-signal",
  Concept: "bg-acid",
};

export function Status({ status }: { status: keyof typeof STATUS }) {
  return (
    <span className="label inline-flex items-center gap-2">
      <span className={cn("size-2", STATUS[status])} />
      {status}
    </span>
  );
}
