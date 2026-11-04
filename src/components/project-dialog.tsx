"use client";

import { X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { Dialog } from "radix-ui";
import { createContext, useContext, useState } from "react";
import { allProjects, type Project } from "@/data/projects";
import { Cta } from "./cta";
import { ProjectFacts, ProjectScreens } from "./project-parts";
import { Status } from "./shot";

const OpenProject = createContext<(slug: string) => void>(() => {});
export const useOpenProject = () => useContext(OpenProject);

export const projectPath = (slug: string) => `/work/${slug}`;

// A plain left click opens the quick view. Modified clicks keep the link.
export const opensInPlace = (e: React.MouseEvent) =>
  e.button === 0 && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey;

// A project link that opens the quick view in place. It is still a real link,
// so crawlers find the project's page and a modified click (new tab, new
// window) goes straight there.
export function useProjectLink(slug: string) {
  const open = useOpenProject();
  return {
    href: projectPath(slug),
    onClick: (e: React.MouseEvent<HTMLAnchorElement>) => {
      if (!opensInPlace(e)) return;
      e.preventDefault();
      open(slug);
    },
  };
}

const EASE = [0.7, 0, 0.2, 1] as const;

export function ProjectDialogProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [slug, setSlug] = useState<string | null>(null);
  const project = allProjects.find((p) => p.slug === slug);

  return (
    <OpenProject.Provider value={setSlug}>
      {children}
      <Dialog.Root open={!!project} onOpenChange={(o) => !o && setSlug(null)}>
        <AnimatePresence>
          {project && (
            <Dialog.Portal forceMount>
              <Dialog.Overlay asChild forceMount>
                <motion.div
                  className="fixed inset-0 z-[55] bg-black/70"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.4 }}
                />
              </Dialog.Overlay>
              <Dialog.Content asChild forceMount>
                <motion.div
                  className="fixed inset-x-0 top-[5svh] bottom-0 z-[56] overflow-y-auto overscroll-contain bg-background text-foreground outline-none"
                  initial={{ y: "100%" }}
                  animate={{ y: "0%" }}
                  exit={{ y: "100%" }}
                  transition={{ duration: 0.7, ease: EASE }}
                >
                  <Sheet project={project} />
                </motion.div>
              </Dialog.Content>
            </Dialog.Portal>
          )}
        </AnimatePresence>
      </Dialog.Root>
    </OpenProject.Provider>
  );
}

function Sheet({ project }: { project: Project }) {
  return (
    <div className="shell pb-16">
      <div className="sticky top-0 z-10 flex items-center justify-between gap-6 bg-background py-4">
        <Status status={project.status} />
        <Dialog.Close
          aria-label="Close project"
          className="group grid size-10 place-items-center bg-foreground text-background transition-colors hover:bg-signal hover:text-[#11110f]"
        >
          <X className="size-5 transition-transform duration-300 group-hover:rotate-90" />
        </Dialog.Close>
      </div>

      <div className="grid grid-cols-12 gap-x-4 sm:gap-x-8 gap-y-10 pt-4">
        <div className="col-span-12 lg:col-span-4">
          <div className="flex flex-col gap-7 lg:sticky lg:top-24">
            <Dialog.Title className="display text-[clamp(2.75rem,5.6vw,5.5rem)]">
              {project.name}
            </Dialog.Title>
            <p className="label text-muted-foreground">
              {[project.kind, project.sector, project.place]
                .filter(Boolean)
                .join(" / ")}
            </p>
            <Dialog.Description className="text-xl leading-snug text-pretty">
              {project.summary}
            </Dialog.Description>
            <ProjectFacts project={project} />
            <Cta href={projectPath(project.slug)} size="lg">
              Full case study
            </Cta>
          </div>
        </div>

        <div className="col-span-12 flex flex-col gap-6 lg:col-span-8">
          <ProjectScreens project={project} />
        </div>
      </div>
    </div>
  );
}
