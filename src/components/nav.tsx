"use client";

import { ArrowUpRight } from "lucide-react";
import { motion, useMotionValueEvent, useScroll } from "motion/react";
import { useState } from "react";
import { site } from "@/lib/site";
import { cn } from "@/lib/utils";
import { SNMark } from "./logo";
import { ThemeToggle } from "./theme-toggle";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
  SheetTrigger,
} from "./ui/sheet";

// A cell of the bar. On hover a block rises from the bottom and the text inverts.
const CELL =
  "group/cell relative flex items-center overflow-hidden border-border px-4 before:absolute before:inset-0 before:translate-y-full before:bg-foreground before:transition-transform before:duration-300 before:ease-swift hover:before:translate-y-0";
const INK = "relative transition-colors duration-300 group-hover/cell:text-background";

// The header is one ruled bar cut into cells: mark, links, theme switch, call to action.
// It floats a little below the top edge and tucks away while scrolling down.
export function Nav() {
  const { scrollY } = useScroll();
  const [hidden, setHidden] = useState(false);
  const [open, setOpen] = useState(false);

  useMotionValueEvent(scrollY, "change", (y) => {
    const before = scrollY.getPrevious() ?? 0;
    setHidden(y > before && y > 500);
  });

  function jump(e: React.MouseEvent<HTMLAnchorElement>, href: string) {
    e.preventDefault();
    setOpen(false);
    setTimeout(() => document.querySelector(href)?.scrollIntoView(), 320);
  }

  return (
    <motion.header
      className="fixed inset-x-0 top-0 z-50"
      animate={{ y: hidden && !open ? "-120%" : "0%" }}
      transition={{ duration: 0.5, ease: [0.7, 0, 0.2, 1] }}
    >
      <div className="shell pt-3">
        <div className="flex h-12 items-stretch border border-border bg-background">
          <a
            href="#top"
            aria-label="Synex Labs, back to top"
            data-cursor="Top"
            className="flex items-center gap-2.5 border-r border-border px-3 md:px-4"
          >
            <SNMark className="size-6" ghosts={false} />
            <span className="wide text-[0.72rem] max-sm:hidden">Synex Labs</span>
          </a>

          <nav aria-label="Main" className="hidden items-stretch md:flex">
            {site.nav.map((item, i) => (
              <a
                key={item.href}
                href={item.href}
                className={cn(CELL, "label gap-2 border-r")}
              >
                <span className={cn(INK, "text-signal")}>0{i + 1}</span>
                <span className={INK}>{item.label}</span>
              </a>
            ))}
          </nav>

          <ThemeToggle className="ml-auto h-full border-l border-border" />
          <a
            href="#contact"
            className="group hidden items-center gap-3 bg-foreground px-4 text-sm font-semibold text-background transition-colors duration-300 hover:bg-signal hover:text-[#11110f] sm:flex"
          >
            Start a project
            <ArrowUpRight className="size-4 transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </a>

          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <button
                type="button"
                aria-label="Open menu"
                className="grid w-12 place-items-center border-l border-border md:hidden"
              >
                <span className="grid gap-1.5">
                  <span className="block h-0.5 w-5 bg-foreground" />
                  <span className="block h-0.5 w-3 justify-self-end bg-signal" />
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
                className="flex flex-1 flex-col justify-center px-5"
              >
                {[...site.nav, { label: "Contact", href: "#contact" }].map(
                  (item, i) => (
                    <a
                      key={item.href}
                      href={item.href}
                      onClick={(e) => jump(e, item.href)}
                      className="title flex items-baseline justify-between border-b border-border py-4 text-[2.6rem] active:text-signal"
                    >
                      {item.label}
                      <span className="label text-muted-foreground">
                        0{i + 1}
                      </span>
                    </a>
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
