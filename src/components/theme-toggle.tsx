"use client";

import { Moon, Sun } from "lucide-react";
import { useLayoutEffect } from "react";
import { cn } from "@/lib/utils";

// Runs before the page paints: applies the saved theme. Scroll restoration is
// manual so reloads start at the top, but the URL hash is preserved so
// deep links (#work, #contact) and the back button keep working.
export const themeScript = `(function(){try{document.documentElement.setAttribute("data-theme",localStorage.getItem("theme")==="dark"?"dark":"light")}catch(e){}try{history.scrollRestoration="manual"}catch(e){}})()`;

function resolveTheme() {
  // Light is the house default. Dark is one click away and is remembered.
  return localStorage.getItem("theme") === "dark" ? "dark" : "light";
}

// A two-square switch: sun on the left, moon on the right. The orange block
// slides under whichever is active.
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
      className={cn("group flex items-center gap-3 px-3", className)}
    >
      <span className="label max-xl:hidden">
        <span className="dark:hidden">Light</span>
        <span className="hidden dark:inline">Dark</span>
      </span>
      <span className="relative grid h-7 w-14 grid-cols-2 border border-foreground/60 transition-colors duration-300 group-hover:border-foreground">
        <span
          aria-hidden
          className="absolute inset-y-0 left-0 w-1/2 bg-signal transition-transform duration-500 ease-swift dark:translate-x-full"
        />
        <Sun className="relative m-auto size-3.5 text-[#11110f] transition-colors duration-300 dark:text-foreground/60" />
        <Moon className="relative m-auto size-3.5 text-foreground/50 transition-colors duration-300 dark:text-[#11110f]" />
      </span>
    </button>
  );
}
