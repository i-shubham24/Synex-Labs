"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { finishIntro } from "./intro";
import { SNLogo } from "./logo";

export function Preloader() {
  const [open, setOpen] = useState(true);
  const [trip, setTrip] = useState(false);

  useEffect(() => {
    const spread = setTimeout(() => setTrip(true), 250);
    const close = setTimeout(() => {
      setOpen(false);
      finishIntro();
    }, 1150);
    return () => {
      clearTimeout(spread);
      clearTimeout(close);
    };
  }, []);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="curtain"
          className="surface-invert fixed inset-0 z-[80] grid place-items-center"
          initial={{ clipPath: "polygon(0% 0%, 200% 0%, 0% 200%)" }}
          exit={{ clipPath: "polygon(0% 0%, 0% 0%, 0% 0%)" }}
          transition={{ duration: 0.85, ease: [0.7, 0, 0.2, 1] }}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.7, opacity: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          >
            <SNLogo trip={trip} className="text-[clamp(4.5rem,14vw,9rem)]" />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
