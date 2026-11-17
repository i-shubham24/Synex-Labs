import { Plus } from "lucide-react";
import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Cta } from "@/components/cta";
import { Fade, Label, Rise } from "@/components/reveal";
import { Footer } from "@/components/sections/footer";
import { Status } from "@/components/shot";
import { findNiche, niches, type Niche } from "@/data/niches";
import { servicePackages } from "@/data/packages";
import { allProjects, cover, type Project } from "@/data/projects";
import { bookingUrl, whatsappLink } from "@/lib/contact";
import { site } from "@/lib/site";

type Props = { params: Promise<{ niche: string }> };

// One static page per niche; anything else is a 404 (static export).
export const dynamicParams = false;

export function generateStaticParams() {
  return niches.map((n) => ({ niche: n.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const niche = findNiche((await params).niche);
  if (!niche) return {};
  const title = `Websites for ${niche.plural.toLowerCase()} in India`;
  const url = `/websites-for/${niche.slug}`;
  return {
    title,
    description: niche.intro,
    alternates: { canonical: url },
    openGraph: {
      type: "website",
      url,
      siteName: site.name,
      locale: site.locale,
      title: `${title} | ${site.name}`,
      description: niche.intro,
    },
    twitter: {
      card: "summary_large_image",
      title: `${title} | ${site.name}`,
      description: niche.intro,
      creator: site.twitterHandle,
    },
  };
}

function packageFor(niche: Niche) {
  return servicePackages.find((p) => p.id === niche.packageId) ?? servicePackages[0];
}

function workFor(niche: Niche): { label: string; items: Project[] } {
  const related = niche.related
    .map((slug) => allProjects.find((p) => p.slug === slug))
    .filter((p): p is Project => Boolean(p));
  if (related.length) return { label: "Related work", items: related.slice(0, 3) };
  const recent = allProjects.filter((p) => p.kind === "Website" && p.status !== "Concept").slice(0, 3);
  return { label: "Recent work", items: recent };
}

function faqsFor(niche: Niche) {
  const pkg = packageFor(niche);
  return [
    {
      q: `How much does a ${niche.singular} website cost?`,
      a: "It depends on the pages and features you need. After a short call we send you a fixed quote, before any work starts.",
    },
    {
      q: "How long does it take?",
      a: `About ${pkg.timelineDays} days for most projects, once we have your logo, photos and details.`,
    },
    {
      q: "What do you need from me?",
      a: "Your logo, a few photos, your services and contact details. We help write the text and handle the setup.",
    },
    {
      q: "Will it show up on Google?",
      a: "We set up what Google needs: clear titles, proper page structure and your location details. Rankings take time and also depend on your Google Business Profile, which we can help you set up.",
    },
  ];
}

export default async function NichePage({ params }: Props) {
  const niche = findNiche((await params).niche);
  if (!niche) notFound();

  const pkg = packageFor(niche);
  const work = workFor(niche);
  const faqs = faqsFor(niche);
  const wa = whatsappLink(`Hi Synex Labs, I would like a website for my ${niche.singular}.`);
  const url = `${site.url}/websites-for/${niche.slug}`;

  const serviceJsonLd = {
    "@context": "https://schema.org",
    "@type": "Service",
    name: `Website design for ${niche.plural.toLowerCase()}`,
    serviceType: "Website design and development",
    provider: { "@type": "Organization", name: site.name, url: site.url },
    areaServed: { "@type": "Country", name: "India" },
    url,
    description: niche.intro,
  };
  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((f) => ({
      "@type": "Question",
      name: f.q,
      acceptedAnswer: { "@type": "Answer", text: f.a },
    })),
  };

  return (
    <>
      {[serviceJsonLd, faqJsonLd].map((data, i) => (
        <script
          key={i}
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, "\\u003c") }}
        />
      ))}
      <main id="top" className="pt-28 pb-24 md:pt-40 md:pb-36">
        <div className="shell">
          {/* Hero */}
          <Label index="IN">Websites for {niche.plural.toLowerCase()}</Label>
          <div className="mt-8 grid grid-cols-12 items-end gap-x-4 gap-y-10 sm:gap-x-8 md:mt-12">
            <h1 className="title col-span-12 text-[clamp(2.8rem,7vw,7rem)] lg:col-span-8">
              {/* afterIntro: the hero is on screen at load (a wrapped line never trips whileInView) */}
              <Rise afterIntro>{niche.title[0]}</Rise>
              <Rise afterIntro delay={0.08}>
                <em>{niche.title[1]}</em>
              </Rise>
            </h1>
            <Fade className="col-span-12 lg:col-span-4" delay={0.15}>
              <p className="max-w-md text-lg leading-snug text-pretty">{niche.intro}</p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Cta href={wa ?? "/#contact"} external={Boolean(wa)} tone="signal" size="lg" className="min-w-56">
                  {wa ? "Message us on WhatsApp" : "Start a project"}
                </Cta>
                {bookingUrl && (
                  <Cta href={bookingUrl} external tone="solid" size="lg">
                    Book a call
                  </Cta>
                )}
              </div>
            </Fade>
          </div>

          {/* Quote + includes */}
          <Fade className="mt-16 md:mt-24">
            <div className="grid border-t border-l border-border md:grid-cols-12">
              <div className="flex flex-col justify-between gap-8 border-r border-b border-border p-6 md:col-span-4 md:p-9">
                <p className="label text-muted-foreground">Price</p>
                <div>
                  <p className="title text-[clamp(2.4rem,4.5vw,4rem)]">A fixed quote for you</p>
                  <p className="mt-3 text-muted-foreground">
                    After a short call you get one clear price, before any work starts. Most sites take about{" "}
                    {pkg.timelineDays} days.
                  </p>
                </div>
                <Link
                  href={wa ?? "/#contact"}
                  {...(wa ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                  className="label w-fit underline decoration-border underline-offset-4 transition-colors hover:decoration-signal"
                >
                  Ask for a quote
                </Link>
              </div>
              <div className="border-r border-b border-border p-6 md:col-span-8 md:p-9">
                <p className="label text-muted-foreground">What your {niche.singular} website includes</p>
                <ul className="mt-6 grid gap-x-8 gap-y-4 sm:grid-cols-2">
                  {niche.includes.map((item) => (
                    <li key={item} className="flex gap-3 text-lg leading-snug">
                      <span aria-hidden className="mt-[0.5em] size-2 shrink-0 bg-signal" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Fade>

          {/* How it works */}
          <div className="mt-20 md:mt-28">
            <Label index="01">How it works</Label>
            <Fade className="mt-8 grid border-t border-l border-border md:mt-10 md:grid-cols-3">
              {[
                ["Free call", `We learn about your ${niche.singular} and what you want people to do on the site.`],
                ["Design and build", `About ${pkg.timelineDays} days. You review a preview and we adjust it.`],
                ["Go live", "We launch it, connect your domain and set up the Google basics."],
              ].map(([head, text], i) => (
                <div key={head} className="flex flex-col gap-6 border-r border-b border-border p-6 md:p-9">
                  <span className="label text-signal">0{i + 1}</span>
                  <div>
                    <p className="title text-3xl md:text-4xl">{head}</p>
                    <p className="mt-3 max-w-sm text-pretty text-muted-foreground">{text}</p>
                  </div>
                </div>
              ))}
            </Fade>
          </div>

          {/* Work */}
          {work.items.length > 0 && (
            <div className="mt-20 md:mt-28">
              <Label index="02">{work.label}</Label>
              <Fade className="mt-8 grid gap-6 sm:grid-cols-2 md:mt-10 lg:grid-cols-3">
                {work.items.map((p) => (
                  <Link key={p.slug} href={`/work/${p.slug}`} className="group block">
                    <div className="relative aspect-[16/10] overflow-hidden border border-border bg-foreground/5">
                      <Image
                        src={cover(p)}
                        alt={`${p.name} website`}
                        fill
                        sizes="(max-width: 640px) 92vw, (max-width: 1024px) 46vw, 30vw"
                        className="object-cover object-top transition-transform duration-700 ease-swift group-hover:scale-[1.03]"
                      />
                    </div>
                    <div className="mt-4 flex items-start justify-between gap-4">
                      <div>
                        <p className="title text-2xl">{p.name}</p>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {p.kind} · {p.sector}
                        </p>
                      </div>
                      <Status status={p.status} />
                    </div>
                  </Link>
                ))}
              </Fade>
            </div>
          )}

          {/* FAQ */}
          <div className="mt-20 md:mt-28">
            <Label index="03">Questions</Label>
            <Fade className="mt-8 border-t border-border md:mt-10">
              {faqs.map((f) => (
                <details key={f.q} className="group border-b border-border">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-6 py-5 text-xl md:py-6 md:text-2xl [&::-webkit-details-marker]:hidden">
                    <span>{f.q}</span>
                    <span className="grid size-9 shrink-0 place-items-center bg-foreground/10 transition-colors duration-300 group-open:bg-signal group-open:text-[#11110f]">
                      <Plus aria-hidden className="size-4 transition-transform duration-300 group-open:rotate-45" />
                    </span>
                  </summary>
                  <p className="max-w-2xl pb-6 text-lg leading-snug text-pretty text-muted-foreground">{f.a}</p>
                </details>
              ))}
            </Fade>
          </div>

          {/* Closing CTA */}
          <Fade className="mt-20 flex flex-wrap items-center justify-between gap-5 border border-border p-6 md:mt-28 md:p-9">
            <p className="title text-2xl md:text-3xl">
              Ready for your {niche.singular} website? <i>Let us talk.</i>
            </p>
            <Cta href={wa ?? "/#contact"} external={Boolean(wa)} tone="signal" size="lg" className="min-w-52">
              {wa ? "WhatsApp us" : "Start a project"}
            </Cta>
          </Fade>

          {/* Other niches, for people and crawlers */}
          <p className="mt-10 text-muted-foreground">
            Also for{" "}
            {niches
              .filter((n) => n.slug !== niche.slug)
              .map((n, i, list) => (
                <span key={n.slug}>
                  <Link
                    href={`/websites-for/${n.slug}`}
                    className="text-foreground underline decoration-border underline-offset-4 transition-colors hover:decoration-signal"
                  >
                    {n.plural.toLowerCase()}
                  </Link>
                  {i < list.length - 2 ? ", " : i === list.length - 2 ? " and " : "."}
                </span>
              ))}
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}
