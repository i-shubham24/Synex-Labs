"use client";

import { useLenis } from "lenis/react";
import { X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Image from "next/image";
import { Dialog } from "radix-ui";
import { createContext, useContext, useEffect, useState } from "react";
import { frames, mobileShot, projects, type Project } from "@/data/projects";
import { Cta } from "./cta";
import { Frame, Status } from "./shot";

const OpenProject = createContext<(slug: string) => void>(() => {});
export const useOpenProject = () => useContext(OpenProject);

const EASE = [0.7, 0, 0.2, 1] as const;

export function ProjectDialogProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [slug, setSlug] = useState<string | null>(null);
  const project = projects.find((p) => p.slug === slug);
  const lenis = useLenis();

  useEffect(() => {
    if (!lenis) return;
    if (slug) lenis.stop();
    else lenis.start();
  }, [slug, lenis]);

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
                  data-lenis-prevent
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
  const shots = frames(project);
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

      <div className="grid grid-cols-12 gap-x-8 gap-y-10 pt-4">
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

            <div className="grid grid-cols-2 gap-6">
              <div>
                <p className="label mb-3 text-muted-foreground">What we built</p>
                <ul className="flex flex-col gap-1.5">
                  {project.built.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              {project.stack.length > 0 && (
                <div>
                  <p className="label mb-3 text-muted-foreground">Built with</p>
                  <ul className="flex flex-col gap-1.5">
                    {project.stack.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {project.url && (
              <Cta href={project.url} external tone="signal" size="lg">
                Visit the live site
              </Cta>
            )}
          </div>
        </div>

        <div className="col-span-12 flex flex-col gap-6 lg:col-span-8">
          {shots.map((src, i) => (
            <Frame key={src} url={project.url}>
              <Image
                src={src}
                alt={`${project.name}, screen ${i + 1}`}
                width={1440}
                height={900}
                sizes="(max-width: 1024px) 92vw, 62vw"
                className="h-auto w-full"
              />
            </Frame>
          ))}
          <div className="flex items-end gap-6">
            <div className="w-40 shrink-0 bg-card p-1.5 sm:w-52">
              <Image
                src={mobileShot(project)}
                alt={`${project.name} on a phone`}
                width={390}
                height={844}
                sizes="208px"
                className="h-auto w-full"
              />
            </div>
            <p className="label max-w-[16rem] pb-2 text-muted-foreground">
              Captured from the real site on desktop and phone.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
