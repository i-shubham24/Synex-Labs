"use client";

import { useLayoutEffect } from "react";
import { cn } from "@/lib/utils";

export const themeScript = `(function(){try{var t=localStorage.getItem("theme");if(t!=="dark"){t="light"}document.documentElement.setAttribute("data-theme",t)}catch(e){}})()`;

function resolveTheme() {
  // Light is the house default. Dark is one click away and is remembered.
  return localStorage.getItem("theme") === "dark" ? "dark" : "light";
}

export function ThemeToggle({ className }: { className?: string }) {
  // React resets <html> attributes on the dev remount, so put the theme back.
  useLayoutEffect(() => {
    document.documentElement.setAttribute("data-theme", resolveTheme());
  }, []);

  function toggle() {
    const root = document.documentElement;
    const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    const apply = () => {
      root.setAttribute("data-theme", next);
      localStorage.setItem("theme", next);
    };
    const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (still || !document.startViewTransition) apply();
    else document.startViewTransition(apply);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label="Switch between light and dark theme"
      data-cursor="Theme"
      className={cn(
        "group relative grid size-10 place-items-center text-foreground",
        className,
      )}
    >
      <span className="relative block size-5 overflow-hidden bg-foreground transition-transform duration-500 ease-swift group-hover:rotate-90">
        <span className="absolute inset-0 bg-signal [clip-path:polygon(0_0,100%_0,100%_100%)] transition-[clip-path] duration-500 ease-swift dark:[clip-path:polygon(0_0,0_100%,100%_100%)]" />
      </span>
    </button>
  );
}
