"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { finishIntro } from "./intro";
import { LiquidMark } from "./liquid-mark";

// Opening screen: the same liquid SN mark as the hero, melting between S
// and N on the GPU (one canvas layer, no SVG repaint), then the screen wipes
// away along the diagonal.
export function Preloader() {
  const [open, setOpen] = useState(true);

  useEffect(() => {
    const close = setTimeout(() => {
      setOpen(false);
      finishIntro();
    }, 1650);
    return () => clearTimeout(close);
  }, []);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="curtain"
          aria-hidden
          className="fixed inset-0 z-[80] grid place-items-center bg-background text-foreground"
          initial={{ clipPath: "polygon(0% 0%, 200% 0%, 0% 200%)" }}
          exit={{ clipPath: "polygon(0% 0%, 0% 0%, 0% 0%)" }}
          transition={{ duration: 0.8, ease: [0.7, 0, 0.2, 1] }}
        >
          <motion.div
            // No entrance animation: the mark must be on screen before any script runs.
            initial={false}
            exit={{ scale: 0.6, opacity: 0 }}
            transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
          >
            <LiquidMark className="w-[clamp(8rem,15vw,11.5rem)]" />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
