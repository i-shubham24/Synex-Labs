import { ArrowUpRight } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { Cta, RollLink } from "@/components/cta";
import { ProjectFacts, ProjectScreens } from "@/components/project-parts";
import { Fade, Rise } from "@/components/reveal";
import { Footer } from "@/components/sections/footer";
import { Status } from "@/components/shot";
import { allProjects, moreProjects } from "@/data/projects";
import { site } from "@/lib/site";

type Props = { params: Promise<{ slug: string }> };

// The whole page is static. An unknown slug waits for its real render (a
// 404) instead of being served the generic shell with a 200 first.
export const ensureStatic = "navigation";

// Every project gets a page at build time. Unknown slugs 404 in the page.
export function generateStaticParams() {
  return allProjects.map((project) => ({ slug: project.slug }));
}

const find = (slug: string) => allProjects.find((p) => p.slug === slug);

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const project = find(slug);
  if (!project) return {};
  const title = `${project.name} | ${project.kind} for ${project.sector.toLowerCase()}`;
  return {
    title,
    description: project.summary,
    alternates: { canonical: `/work/${project.slug}` },
    openGraph: {
      type: "article",
      url: `/work/${project.slug}`,
      siteName: site.name,
      locale: site.locale,
      title: `${title} | ${site.name}`,
      description: project.summary,
    },
    twitter: {
      card: "summary_large_image",
      title: `${title} | ${site.name}`,
      description: project.summary,
      creator: site.twitterHandle,
    },
  };
}

// The frame of the page is the same for every project, so it stays in the
// shared App Shell. Only the parts that read the slug wait behind Suspense.
export default function ProjectPage({ params }: Props) {
  return (
    <>
      <main id="top" className="pt-24 pb-24 md:pt-32 md:pb-36">
        <div className="shell">
          <Suspense fallback={<div aria-hidden className="min-h-svh" />}>
            <ProjectDetail params={params} />
          </Suspense>

          <Fade className="mt-20 flex flex-wrap items-center justify-between gap-5 border border-border p-6 md:mt-28 md:p-9">
            <p className="title text-2xl md:text-3xl">
              Want something like this? <i>Let us talk.</i>
            </p>
            <Cta href="/#contact" tone="signal" size="lg" className="min-w-52">
              Start a project
            </Cta>
          </Fade>

          <Suspense fallback={null}>
            <NextProject params={params} />
          </Suspense>
        </div>
      </main>
      <Footer />
    </>
  );
}

async function ProjectDetail({ params }: Props) {
  const { slug } = await params;
  const project = find(slug);
  if (!project) notFound();

  const own = !moreProjects.includes(project);
  const pageUrl = `${site.url}/work/${project.slug}`;

  const jsonLd = [
    {
      "@context": "https://schema.org",
      "@type": "CreativeWork",
      name: project.name,
      headline: `${project.name}, ${project.kind.toLowerCase()} for ${project.sector.toLowerCase()}`,
      description: project.summary,
      url: pageUrl,
      ...(project.url && { sameAs: project.url }),
      genre: project.kind,
      keywords: [project.sector, ...project.stack].join(", "),
      creator: { "@type": "Organization", name: site.name, url: site.url },
    },
    {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: "Home", item: site.url },
        { "@type": "ListItem", position: 2, name: "Work", item: `${site.url}/#work` },
        { "@type": "ListItem", position: 3, name: project.name, item: pageUrl },
      ],
    },
  ];

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c"),
        }}
      />
      <nav
        aria-label="Breadcrumb"
        className="label flex flex-wrap items-center gap-2.5 text-muted-foreground"
      >
        <span aria-hidden className="size-1.5 bg-signal" />
        <RollLink href="/#work">{own ? "Work" : "More projects"}</RollLink>
        <span aria-hidden>/</span>
        <span className="text-foreground">{project.name}</span>
      </nav>

      <div className="grid grid-cols-12 gap-x-4 gap-y-10 pt-10 sm:gap-x-8 md:pt-14">
        <div className="col-span-12 lg:col-span-4">
          <div className="flex flex-col gap-7 lg:sticky lg:top-24">
            <Status status={project.status} />
            <h1 className="display text-[clamp(2.75rem,5.6vw,5.5rem)]">
              <Rise afterIntro>{project.name}</Rise>
            </h1>
            <p className="label text-muted-foreground">
              {[project.kind, project.sector, project.place]
                .filter(Boolean)
                .join(" / ")}
            </p>
            <p className="text-xl leading-snug text-pretty">{project.summary}</p>
            <ProjectFacts project={project} />
          </div>
        </div>

        <div className="col-span-12 flex flex-col gap-6 lg:col-span-8">
          <ProjectScreens project={project} priority />
        </div>
      </div>
    </>
  );
}

async function NextProject({ params }: Props) {
  const { slug } = await params;
  const project = find(slug);
  if (!project) return null;
  const next = allProjects[(allProjects.indexOf(project) + 1) % allProjects.length];

  return (
    <Fade className="mt-16 border-t border-border pt-6 md:mt-24">
      {/* Prefetched, so the next project's details are ready before the click. */}
      <Link
        href={`/work/${next.slug}`}
        prefetch
        data-cursor="Next"
        className="group flex flex-col gap-3"
      >
        <span className="label text-muted-foreground">Next project</span>
        <span className="display flex items-center justify-between gap-6 text-[clamp(2.4rem,7vw,7rem)] transition-colors duration-300 group-hover:text-signal">
          {next.name}
          <ArrowUpRight className="size-[0.55em] shrink-0 transition-transform duration-300 group-hover:translate-x-1 group-hover:-translate-y-1" />
        </span>
      </Link>
    </Fade>
  );
}
