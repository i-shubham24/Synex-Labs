"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { finishIntro } from "./intro";
import { LiquidMark } from "./liquid-mark";

// Opening screen: the same liquid SN mark as the hero goes from S to N once,
// then the screen wipes away along the diagonal. It plays once per visit:
// later pages in the same tab session start with the curtain already gone.
export function Preloader() {
  const [open, setOpen] = useState(true);
  const mark = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let waiting = true;
    const close = () => {
      if (!waiting) return;
      waiting = false;
      setOpen(false);
      finishIntro();
      try {
        sessionStorage.setItem("intro", "seen");
      } catch {}
    };
    if (document.documentElement.dataset.intro === "seen") {
      close();
      return;
    }
    // The mark starts its pass in CSS before any script runs. Lift the curtain
    // the moment that pass is over, however late this code arrives.
    const pass = (mark.current?.getAnimations?.({ subtree: true }) ?? []).filter(
      (a) => a instanceof CSSAnimation,
    );
    Promise.allSettled(pass.map((a) => a.finished)).then(close);
    const limit = setTimeout(close, 2400);
    return () => {
      waiting = false;
      clearTimeout(limit);
    };
  }, []);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="curtain"
          aria-hidden
          className="curtain fixed inset-0 z-[80] grid place-items-center bg-background text-foreground"
          initial={{ clipPath: "polygon(0% 0%, 200% 0%, 0% 200%)" }}
          exit={{ clipPath: "polygon(0% 0%, 0% 0%, 0% 0%)" }}
          transition={{ duration: 0.8, ease: [0.7, 0, 0.2, 1] }}
        >
          <motion.div
            ref={mark}
            // No entrance animation: the mark must be on screen before any script runs.
            initial={false}
            exit={{ scale: 0.6, opacity: 0 }}
            transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
          >
            <LiquidMark once className="w-[clamp(16rem,30vw,24rem)]" />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
