"use client";

import { ArrowUpRight } from "lucide-react";
import { motion, useReducedMotion, useScroll, useTransform } from "motion/react";
import Image from "next/image";
import { useRef, useState } from "react";
import {
  cover,
  frames,
  moreProjects,
  projects,
  type Project,
} from "@/data/projects";
import { cn } from "@/lib/utils";
import { BoxField } from "../box-field";
import { useOpenProject } from "../project-dialog";
import { Fade, SectionHead } from "../reveal";
import { Frame, Shot, Status } from "../shot";

export function Work() {
  const sectionRef = useRef<HTMLElement>(null);
  const still = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start end", "end start"],
  });
  const boxY = useTransform(scrollYProgress, [0, 1], ["-25%", "35%"]);
  const boxRotate = useTransform(scrollYProgress, [0, 1], [-14, 18]);
  const boxScale = useTransform(scrollYProgress, [0, 0.5, 1], [0.92, 1.1, 0.94]);

  return (
    <section ref={sectionRef} id="work" className="overflow-x-clip pt-24 md:pt-36">
      <div className="shell relative">
        {/* A disc of small boxes behind the intro text with 3D depth parallax. */}
        <motion.div
          aria-hidden
          style={{ y: still ? 0 : boxY, rotate: still ? 0 : boxRotate, scale: still ? 1 : boxScale }}
          className="pointer-events-none absolute -top-44 -right-[5%] w-[min(64vw,36rem)] max-lg:opacity-50 will-change-transform"
        >
          <BoxField className="size-full" />
        </motion.div>
        <SectionHead
          className="relative"
          index="01"
          label="Work"
          title={[
            <>Real sites for</>,
            <>
              <em>real clients.</em>
            </>,
          ]}
          aside={
            <>
              {projects.length} projects for clients in three countries. Hover
              a row to see the site, click it to open every screen.
            </>
          }
        />

        <Fade className="mt-14 md:mt-20">
          <ul className="border-t border-border">
            {projects.map((project) => (
              <Slab key={project.slug} project={project} />
            ))}
          </ul>
        </Fade>
      </div>
      <More />
    </section>
  );
}

// One project per row. On hover the row turns into a dark slab, its screen
// slides in beside the name and the name moves over to make room.
// In dark mode the slab is a raised dark tone, not paper, so nothing flashes white.
function Slab({ project }: { project: Project }) {
  const open = useOpenProject();
  return (
    <li className="group relative border-b border-border">
      <span
        aria-hidden
        className="absolute -inset-y-px inset-x-0 rounded-[10px] bg-foreground opacity-0 transition-opacity duration-300 lg:group-hover:opacity-100 dark:bg-secondary"
      />
      <button
        type="button"
        onClick={() => open(project.slug)}
        data-cursor="View project"
        className="relative grid w-full grid-cols-12 items-center gap-x-6 gap-y-4 py-6 text-left transition-colors duration-300 lg:min-h-44 lg:px-6 lg:py-5 lg:group-hover:text-background dark:lg:group-hover:text-foreground"
      >
        <span className="label col-span-12 flex items-center justify-between gap-4 text-muted-foreground lg:col-span-3 lg:text-[0.8rem]">
          <span>2026, {project.sector}</span>
          <span className="lg:hidden">
            <Status status={project.status} />
          </span>
        </span>

        <span className="col-span-12 overflow-hidden rounded-md border border-border sm:col-span-6 lg:absolute lg:top-1/2 lg:left-[24%] lg:w-52 lg:origin-left lg:-translate-y-1/2 lg:scale-90 lg:border-0 lg:opacity-0 lg:transition-[opacity,scale] lg:duration-500 lg:ease-out-soft lg:group-hover:scale-100 lg:group-hover:opacity-100">
          <Image
            src={cover(project)}
            alt={`${project.name} home page`}
            width={1440}
            height={900}
            sizes="(max-width: 640px) 92vw, (max-width: 1024px) 46vw, 220px"
            className="aspect-[16/10] w-full object-cover object-top"
          />
        </span>

        <span className="display col-span-10 text-[clamp(2.4rem,5.4vw,5.6rem)] transition-transform duration-500 ease-out-soft sm:col-span-6 lg:col-span-7 lg:col-start-4 lg:group-hover:translate-x-[12rem] xl:group-hover:translate-x-[15.5rem]">
          {project.name}
        </span>

        <span className="col-span-2 flex items-center justify-end gap-5 lg:col-span-2">
          <span className="max-lg:hidden">
            <Status status={project.status} />
          </span>
          <ArrowUpRight className="size-6 shrink-0 transition-transform duration-300 group-hover:translate-x-1 group-hover:-translate-y-1" />
        </span>
      </button>
    </li>
  );
}

const SPANS = [
  "lg:col-span-7",
  "lg:col-span-5",
  "lg:col-span-5",
  "lg:col-span-7",
  "lg:col-span-4",
  "lg:col-span-4",
  "lg:col-span-4",
  "lg:col-span-4",
  "lg:col-span-4",
  "lg:col-span-4",
];

// The rest of the work as a grid of uneven tiles. Hovering a tile steps through its screens.
function More() {
  return (
    <div className="shell mt-20 grid grid-cols-12 items-start gap-x-6 gap-y-14 md:mt-28">
      <Fade className="col-span-12 flex items-end justify-between gap-6 border-b border-border pb-5">
        <p className="title text-3xl md:text-4xl">More projects</p>
        <p className="label text-muted-foreground">
          {String(moreProjects.length).padStart(2, "0")} projects
        </p>
      </Fade>
      {moreProjects.map((project, i) => (
        <Tile
          key={project.slug}
          project={project}
          className={SPANS[i % SPANS.length]}
          delay={(i % 3) * 0.07}
        />
      ))}
    </div>
  );
}

function Tile({
  project,
  className,
  delay,
}: {
  project: Project;
  className: string;
  delay: number;
}) {
  const open = useOpenProject();
  const [hover, setHover] = useState(false);
  return (
    <Fade className={cn("col-span-12 md:col-span-6", className)} delay={delay}>
      <button
        type="button"
        onClick={() => open(project.slug)}
        onPointerEnter={() => setHover(true)}
        onPointerLeave={() => setHover(false)}
        data-cursor="Open"
        className="group block w-full text-left"
      >
        <Frame url={project.url} className="border border-border">
          <Shot
            frames={frames(project)}
            alt={`${project.name} screens`}
            play={hover}
            sizes="(max-width: 768px) 92vw, (max-width: 1024px) 46vw, 54vw"
          />
        </Frame>
        <span className="mt-4 flex items-start justify-between gap-4">
          <span className="title text-2xl transition-colors group-hover:text-signal md:text-[1.75rem]">
            {project.name}
          </span>
          <Status status={project.status} />
        </span>
        <span className="mt-3 flex flex-wrap gap-1.5">
          <span className="tag border-foreground bg-foreground text-background">
            {project.kind}
          </span>
          <span className="tag">{project.sector}</span>
          {project.place && <span className="tag">{project.place}</span>}
        </span>
      </button>
    </Fade>
  );
}
