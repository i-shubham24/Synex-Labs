"use client";

import {
  motion,
  useScroll,
  useTransform,
  type MotionValue,
} from "motion/react";
import Image from "next/image";
import { useRef, useState } from "react";
import {
  featured,
  frames,
  mobileShot,
  more,
  projects,
  type Project,
} from "@/data/projects";
import { cn } from "@/lib/utils";
import { Cta, RollLink } from "../cta";
import { useOpenProject } from "../project-dialog";
import { Fade, SectionHead } from "../reveal";
import { Frame, Shot, Status } from "../shot";

function Tags({ project, max = 3 }: { project: Project; max?: number }) {
  return (
    <span className="flex flex-wrap gap-1.5">
      <span className="tag border-foreground bg-foreground text-background">
        {project.kind}
      </span>
      <span className="tag">{project.sector}</span>
      {project.stack.slice(0, max).map((item) => (
        <span key={item} className="tag max-sm:hidden">
          {item}
        </span>
      ))}
    </span>
  );
}

export function Work() {
  return (
    <section id="work" className="pt-24 md:pt-36">
      <div className="shell">
        <SectionHead
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
              {projects.length} projects across three countries. Every image
              here is a capture of the real thing. Open one to see more
              screens.
            </>
          }
        />
      </div>
      <Stack />
      <Grid />
    </section>
  );
}

// Four lead projects. On desktop each card pins and the next one slides over it.
function Stack() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end end"],
  });
  return (
    <div ref={ref} className="shell mt-14 flex flex-col gap-6 md:mt-20 lg:gap-0">
      {featured.map((project, i) => (
        <StackCard
          key={project.slug}
          project={project}
          index={i}
          total={featured.length}
          progress={scrollYProgress}
        />
      ))}
    </div>
  );
}

function StackCard({
  project,
  index,
  total,
  progress,
}: {
  project: Project;
  index: number;
  total: number;
  progress: MotionValue<number>;
}) {
  const open = useOpenProject();
  const [hover, setHover] = useState(false);
  const scale = useTransform(
    progress,
    [index / total, 1],
    [1, 1 - (total - 1 - index) * 0.035],
  );

  return (
    <div
      className="lg:sticky lg:h-[calc(100svh-5.5rem)] lg:pb-8"
      style={{ top: `calc(5rem + ${index * 14}px)` }}
    >
      <motion.article
        style={{ scale }}
        className="grid h-full origin-top grid-cols-12 border border-border bg-card max-lg:!transform-none"
      >
        <div className="order-2 col-span-12 flex flex-col justify-between gap-10 p-6 md:p-9 lg:order-1 lg:col-span-5">
          <div className="flex items-center justify-between">
            <span className="label text-muted-foreground">
              <span className="text-signal">0{index + 1}</span> / 0{total}
            </span>
            <Status status={project.status} />
          </div>

          <div className="flex flex-col gap-5">
            <Tags project={project} max={2} />
            <h3 className="title text-[clamp(2.4rem,4.6vw,4.6rem)]">
              {project.name}
            </h3>
            <p className="max-w-md text-lg leading-snug text-pretty">
              {project.summary}
            </p>
            {project.place && (
              <p className="label text-muted-foreground">{project.place}</p>
            )}
          </div>

          <div className="flex flex-col gap-7">
            <ul className="grid gap-1.5 text-[0.95rem]">
              {project.built.map((item) => (
                <li key={item} className="flex items-center gap-3">
                  <span className="size-1.5 shrink-0 bg-signal" />
                  {item}
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
              <Cta onClick={() => open(project.slug)}>View project</Cta>
              {project.url && (
                <RollLink href={project.url} external className="label">
                  Open live site
                </RollLink>
              )}
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={() => open(project.slug)}
          onPointerEnter={() => setHover(true)}
          onPointerLeave={() => setHover(false)}
          data-cursor="Open"
          aria-label={`View ${project.name}`}
          className="relative order-1 col-span-12 flex items-center border-border bg-secondary p-5 max-lg:border-b md:p-9 lg:order-2 lg:col-span-7 lg:border-l"
        >
          <div className="relative w-full">
            <Frame url={project.url} className="shadow-2xl shadow-black/20">
              <Shot
                frames={frames(project)}
                alt={`${project.name} website`}
                play={hover}
                sizes="(max-width: 1024px) 90vw, 52vw"
              />
            </Frame>
            <div className="absolute -bottom-[7%] -left-[3%] w-[19%] bg-card p-1 shadow-2xl shadow-black/30 max-sm:hidden">
              <Image
                src={mobileShot(project)}
                alt=""
                width={390}
                height={844}
                sizes="160px"
                className="h-auto w-full"
              />
            </div>
          </div>
        </button>
      </motion.article>
    </div>
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
];

function Grid() {
  return (
    <div className="shell mt-16 grid grid-cols-12 items-start gap-x-6 gap-y-14 md:mt-24">
      <Fade className="col-span-12 flex items-end justify-between gap-6 border-b border-border pb-5">
        <p className="title text-3xl md:text-4xl">More from the studio</p>
        <p className="label text-muted-foreground">
          {String(more.length).padStart(2, "0")} projects
        </p>
      </Fade>
      {more.map((project, i) => (
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
            alt={`${project.name} website`}
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
        <span className="mt-3 block">
          <Tags project={project} max={0} />
        </span>
      </button>
    </Fade>
  );
}
