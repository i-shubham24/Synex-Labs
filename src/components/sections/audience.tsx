"use client";

import Image from "next/image";
import { audiences } from "@/data/content";
import { cover, projects } from "@/data/projects";
import { useOpenProject } from "../project-dialog";
import { Fade, SectionHead } from "../reveal";

// Who the studio builds for: four cards in a row. A card turns dark under the
// pointer and its example project lifts into view.
export function Audience() {
  const open = useOpenProject();

  return (
    <section id="who" className="pb-24 md:pb-36">
      <div className="shell">
        <SectionHead
          index="04"
          label="Who we work with"
          title={[
            <>Built for teams</>,
            <>
              <i>like yours.</i>
            </>,
          ]}
        />

        <div className="mt-14 grid gap-3 sm:grid-cols-2 md:mt-20 lg:grid-cols-4">
          {audiences.map((item, i) => {
            const project = projects.find((p) => p.slug === item.project)!;
            return (
              <Fade key={item.name} delay={i * 0.08}>
                <article className="group flex h-full flex-col gap-8 bg-card p-5 transition-colors duration-500 hover:bg-foreground hover:text-background md:p-6">
                  <div className="label flex items-center justify-between text-muted-foreground">
                    <span>0{i + 1}</span>
                    <span className="size-2 bg-signal transition-transform duration-500 ease-swift group-hover:scale-[2.2] group-hover:rotate-45" />
                  </div>

                  <button
                    type="button"
                    onClick={() => open(project.slug)}
                    data-cursor="Open"
                    aria-label={`View ${project.name}`}
                    className="overflow-hidden"
                  >
                    <Image
                      src={cover(project)}
                      alt={`${project.name} home page`}
                      width={1440}
                      height={900}
                      sizes="(max-width: 640px) 92vw, (max-width: 1024px) 46vw, 23vw"
                      className="aspect-[16/10] w-full object-cover object-top transition-transform duration-700 ease-out-soft group-hover:scale-105"
                    />
                  </button>

                  <div className="flex flex-1 flex-col gap-3">
                    <h3 className="title text-[1.75rem]">{item.name}</h3>
                    <p className="leading-snug text-pretty opacity-70">
                      {item.line}
                    </p>
                  </div>

                  <ul className="grid gap-1.5 text-[0.95rem]">
                    {item.needs.map((need) => (
                      <li key={need} className="flex items-center gap-3">
                        <span className="size-1.5 shrink-0 bg-signal" />
                        {need}
                      </li>
                    ))}
                  </ul>
                </article>
              </Fade>
            );
          })}
        </div>
      </div>
    </section>
  );
}
