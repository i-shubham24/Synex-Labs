"use client";

import { Plus } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";
import { services, stack } from "@/data/content";
import { frames, projects } from "@/data/projects";
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

  function pick(i: number) {
    if (i === active) return;
    setPrevious(active);
    setActive(i);
  }

  return (
    <section
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

        <div className="mt-14 grid grid-cols-12 gap-x-8 md:mt-20">
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
            <div className="sticky top-28">
              <div className="relative aspect-[16/11.4] overflow-hidden border border-border">
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
  const project = projects.find((p) => p.slug === service.project);
  if (!project)
    return (
      <div className="absolute inset-0 grid place-items-center bg-signal text-[#11110f]">
        <SNMark className="w-2/5" ghosts={false} />
      </div>
    );
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
