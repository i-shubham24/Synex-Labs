import Image from "next/image";
import {
  frames,
  mobileShot,
  moreProjects,
  type Project,
} from "@/data/projects";
import { Cta } from "./cta";
import { Frame } from "./shot";

// What we built, what with, and where to see it live. Shared by the project
// dialog and the project's own page.
export function ProjectFacts({ project }: { project: Project }) {
  return (
    <>
      <div className="grid grid-cols-2 gap-6">
        <div>
          <p className="label mb-3 text-muted-foreground">
            {moreProjects.includes(project) ? "Highlights" : "What we built"}
          </p>
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

      <div className="flex flex-col gap-2">
        {project.url && (
          <Cta href={project.url} external tone="signal" size="lg">
            Visit the live site
          </Cta>
        )}
        {project.appStore && (
          <Cta href={project.appStore} external size="lg">
            App Store
          </Cta>
        )}
        {project.playStore && (
          <Cta href={project.playStore} external size="lg">
            Google Play
          </Cta>
        )}
      </div>
    </>
  );
}

// Every desktop screen in a window frame, then the phone capture.
export function ProjectScreens({
  project,
  priority = false,
}: {
  project: Project;
  // Load the first screen eagerly when it is the page's main image.
  priority?: boolean;
}) {
  return (
    <>
      {frames(project).map((src, i) => (
        <Frame key={src} url={project.url}>
          <Image
            src={src}
            alt={`${project.name}, screen ${i + 1}`}
            width={1440}
            height={900}
            sizes="(max-width: 1024px) 92vw, 62vw"
            priority={priority && i === 0}
            className="h-auto w-full"
          />
        </Frame>
      ))}
      {project.phone !== false && (
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
            {project.kind === "Mobile app"
              ? "Screens taken from the app itself."
              : "Captured from the real site on desktop and phone."}
          </p>
        </div>
      )}
    </>
  );
}
