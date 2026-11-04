"use client";

import { Plus } from "lucide-react";
import { motion, useReducedMotion, useScroll, useTransform } from "motion/react";
import { useRef, useState } from "react";
import { services, stack } from "@/data/content";
import { allProjects, cover, frames } from "@/data/projects";
import { cn } from "@/lib/utils";
import { SNMark } from "../logo";
import { Fade, SectionHead } from "../reveal";
import { Frame, Shot } from "../shot";

const EASE = [0.7, 0, 0.2, 1] as const;
const FULL = "polygon(0% 0%, 200% 0%, 0% 200%)";
const NONE = "polygon(0% 0%, 0% 0%, 0% 0%)";

export function Services() {
  const [active, setActive] = useState(0);
  const [previous, setPrevious] = useState(0);
  const sectionRef = useRef<HTMLElement>(null);
  const still = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start end", "end start"],
  });
  const panelRotateX = useTransform(scrollYProgress, [0.1, 0.5, 0.9], [4, 0, -4]);
  const panelScale = useTransform(scrollYProgress, [0.1, 0.5, 0.9], [0.96, 1, 0.97]);
  const panelY = useTransform(scrollYProgress, [0.1, 0.9], ["-12px", "12px"]);

  function pick(i: number) {
    if (i === active) return;
    setPrevious(active);
    setActive(i);
  }

  return (
    <section
      ref={sectionRef}
      id="services"
      className="surface-invert mt-28 py-24 md:mt-40 md:py-36"
    >
      <div className="shell">
        <SectionHead
          index="02"
          label="Services"
          title={[
            <>What we</>,
            <>
              <i>can build.</i>
            </>,
          ]}
          aside="Five things we do well. Pick one, or mix them into a single project."
        />

        <div className="mt-14 grid grid-cols-12 gap-x-4 sm:gap-x-8 md:mt-20">
          <ul className="col-span-12 flex flex-col border-t border-border lg:col-span-7">
            {services.map((service, i) => {
              const on = i === active;
              return (
                <li key={service.name} className="border-b border-border">
                  <button
                    type="button"
                    onPointerEnter={() => pick(i)}
                    onFocus={() => pick(i)}
                    onClick={() => pick(i)}
                    aria-expanded={on}
                    className="group flex w-full items-start gap-5 py-5 text-left md:py-6"
                  >
                    <span
                      className={cn(
                        "label w-8 shrink-0 pt-3 transition-colors duration-300 md:pt-5",
                        on ? "text-signal" : "text-muted-foreground",
                      )}
                    >
                      0{i + 1}
                    </span>
                    <span className="flex-1">
                      <span
                        className={cn(
                          "title block text-[clamp(2.2rem,5vw,5rem)] transition-colors duration-500",
                          on ? "text-foreground" : "text-foreground/35",
                        )}
                      >
                        {service.name}
                      </span>
                      <motion.span
                        className="block overflow-hidden"
                        initial={false}
                        animate={{
                          height: on ? "auto" : 0,
                          opacity: on ? 1 : 0,
                        }}
                        transition={{ duration: 0.5, ease: EASE }}
                      >
                        <span className="block max-w-xl pt-4 pb-5 text-lg leading-snug text-pretty">
                          {service.line}
                        </span>
                        <span className="flex flex-wrap gap-1.5 pb-2">
                          {service.points.map((point) => (
                            <span key={point} className="tag">
                              {point}
                            </span>
                          ))}
                        </span>
                      </motion.span>
                    </span>
                    <span
                      className={cn(
                        "mt-2 grid size-9 shrink-0 place-items-center transition-colors duration-300 md:mt-4",
                        on
                          ? "bg-signal text-[#11110f]"
                          : "bg-foreground/10 text-foreground",
                      )}
                    >
                      <Plus
                        className={cn(
                          "size-4 transition-transform duration-300",
                          on && "rotate-45",
                        )}
                      />
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="col-span-5 hidden lg:block">
            <div className="sticky top-28 [perspective:1200px]">
              <motion.div
                style={{
                  rotateX: still ? 0 : panelRotateX,
                  scale: still ? 1 : panelScale,
                  y: still ? 0 : panelY,
                  transformStyle: "preserve-3d",
                }}
                className="will-change-transform"
              >
                <div className="relative aspect-[16/11.4] overflow-hidden border border-border shadow-2xl">
                  <Panel index={previous} />
                  <motion.div
                    key={active}
                    className="absolute inset-0"
                    initial={{ clipPath: NONE }}
                    animate={{ clipPath: FULL }}
                    transition={{ duration: 0.75, ease: EASE }}
                  >
                    <Panel index={active} live />
                  </motion.div>
                </div>
                <p className="label mt-3 flex justify-between text-muted-foreground">
                  <span>{services[active].name}</span>
                  <span>
                    0{active + 1} / 0{services.length}
                  </span>
                </p>
              </motion.div>
            </div>
          </div>
        </div>

        <Fade className="mt-20 md:mt-28">
          <p className="label mb-4 text-muted-foreground">Built with</p>
          <ul className="grid grid-cols-2 border-t border-l border-border sm:grid-cols-5">
            {stack.map((item) => (
              <li
                key={item}
                className="group flex items-center gap-3 border-r border-b border-border px-4 py-5 transition-colors duration-300 hover:bg-signal hover:text-[#11110f] md:px-6 md:py-7"
              >
                <span className="size-1.5 shrink-0 bg-signal transition-colors group-hover:bg-[#11110f]" />
                <span className="font-medium">{item}</span>
              </li>
            ))}
          </ul>
        </Fade>
      </div>
    </section>
  );
}

function Panel({ index, live = false }: { index: number; live?: boolean }) {
  const service = services[index];
  const project = allProjects.find((p) => p.slug === service.project);
  if (!project)
    return (
      <div className="absolute inset-0 grid place-items-center bg-signal text-[#11110f]">
        <SNMark className="w-2/5" ghosts={false} />
      </div>
    );
  // Apps are not sites, so no browser frame: the card steps through one board
  // of real screens from every app we have shipped.
  if (project.kind === "Mobile app") {
    const apps = allProjects.filter((p) => p.kind === "Mobile app");
    return (
      <Shot
        frames={apps.map(cover)}
        alt={`Screens from ${apps.map((p) => p.name).join(", ")}`}
        play={live}
        sizes="40vw"
        className="absolute inset-0 aspect-auto"
      />
    );
  }
  return (
    <Frame url={project.url} className="absolute inset-0">
      <Shot
        frames={frames(project)}
        alt={`${project.name} home page preview`}
        play={live}
        sizes="40vw"
        className="aspect-auto h-[calc(100%-1.75rem)]"
      />
    </Frame>
  );
}
