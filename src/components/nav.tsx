"use client";

import { useLenis } from "lenis/react";
import { motion, useMotionValueEvent, useScroll } from "motion/react";
import { useEffect, useState } from "react";
import { site } from "@/lib/site";
import { cn } from "@/lib/utils";
import { Cta, RollLink } from "./cta";
import { SNMark } from "./logo";
import { ThemeToggle } from "./theme-toggle";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
  SheetTrigger,
} from "./ui/sheet";

export function Nav() {
  const { scrollY } = useScroll();
  const [hidden, setHidden] = useState(false);
  const [raised, setRaised] = useState(false);
  const [open, setOpen] = useState(false);
  const lenis = useLenis();

  useMotionValueEvent(scrollY, "change", (y) => {
    const before = scrollY.getPrevious() ?? 0;
    setHidden(y > before && y > 500);
    setRaised(y > 24);
  });

  useEffect(() => {
    if (!lenis) return;
    if (open) lenis.stop();
    else lenis.start();
  }, [open, lenis]);

  function jump(e: React.MouseEvent<HTMLAnchorElement>, href: string) {
    e.preventDefault();
    setOpen(false);
    setTimeout(() => {
      if (lenis) lenis.scrollTo(href, { offset: -72 });
      else document.querySelector(href)?.scrollIntoView();
    }, 320);
  }

  return (
    <motion.header
      className={cn(
        "fixed inset-x-0 top-0 z-50 transition-colors duration-500",
        raised ? "bg-background/88 backdrop-blur-md" : "bg-transparent",
      )}
      animate={{ y: hidden && !open ? "-100%" : "0%" }}
      transition={{ duration: 0.5, ease: [0.7, 0, 0.2, 1] }}
    >
      <div className="shell flex h-16 items-center justify-between gap-6 md:h-[4.5rem]">
        <a
          href="#top"
          className="flex items-center gap-3"
          aria-label="Synex Labs, back to top"
          data-cursor="Top"
        >
          <SNMark className="size-8" />
          <span className="wide hidden text-[0.8rem] sm:block">Synex Labs</span>
        </a>

        <nav aria-label="Main" className="hidden items-center gap-8 md:flex">
          {site.nav.map((item) => (
            <RollLink key={item.href} href={item.href} className="label">
              {item.label}
            </RollLink>
          ))}
        </nav>

        <div className="flex items-center gap-1.5">
          <ThemeToggle />
          <Cta href="#contact" className="hidden sm:inline-flex">
            Start a project
          </Cta>

          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <button
                type="button"
                aria-label="Open menu"
                className="grid size-10 place-items-center md:hidden"
              >
                <span className="grid gap-1.5">
                  <span className="block h-0.5 w-6 bg-foreground" />
                  <span className="block h-0.5 w-4 justify-self-end bg-signal" />
                </span>
              </button>
            </SheetTrigger>
            <SheetContent
              side="right"
              className="surface-invert w-full gap-0 border-0 p-0 data-[side=right]:w-full data-[side=right]:sm:max-w-none"
            >
              <SheetTitle className="sr-only">Menu</SheetTitle>
              <SheetDescription className="sr-only">
                Jump to a section of the page
              </SheetDescription>
              <div className="flex h-16 items-center px-5">
                <SNMark className="size-8" />
              </div>
              <nav
                aria-label="Mobile"
                className="flex flex-1 flex-col justify-center gap-1 px-5"
              >
                {[...site.nav, { label: "Contact", href: "#contact" }].map(
                  (item, i) => (
                    <motion.a
                      key={item.href}
                      href={item.href}
                      onClick={(e) => jump(e, item.href)}
                      className="display text-[clamp(3rem,15vw,5rem)] active:text-signal"
                      initial={{ opacity: 0, x: 40 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{
                        delay: 0.12 + i * 0.05,
                        duration: 0.6,
                        ease: [0.16, 1, 0.3, 1],
                      }}
                    >
                      {item.label}
                    </motion.a>
                  ),
                )}
              </nav>
              <p className="label p-5 text-muted-foreground">{site.email}</p>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </motion.header>
  );
}
