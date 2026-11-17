import { Fragment } from "react";
import { Cta } from "@/components/cta";
import { Fade, SectionHead } from "@/components/reveal";
import { niches } from "@/data/niches";
import { servicePackages } from "@/data/packages";
import { bookingUrl, inr, whatsappLink } from "@/lib/contact";

// Starting prices in rupees (the priority market), with USD for clients abroad.
export function Pricing() {
  return (
    <section id="pricing" className="pt-24 md:pt-36">
      <div className="shell">
        <SectionHead
          index="03"
          label="Pricing"
          title={[
            <Fragment key="l1">Clear prices,</Fragment>,
            <Fragment key="l2">
              <i>in rupees.</i>
            </Fragment>,
          ]}
          aside="Starting prices for each kind of project. After a short call you get a fixed quote, before any work starts."
        />

        <Fade className="mt-14 md:mt-20">
          <ul className="grid border-t border-l border-border sm:grid-cols-2 xl:grid-cols-5">
            {servicePackages.map((pkg, i) => {
              const first = i === 0;
              const wa = whatsappLink(
                `Hi Synex Labs, I am interested in the ${pkg.kind.toLowerCase()} package (from Rs ${inr(pkg.priceInr)}).`,
              );
              return (
                <li
                  key={pkg.id}
                  className="flex flex-col border-r border-b border-border p-6 transition-colors duration-300 hover:bg-foreground/[0.03] md:p-7"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="label text-muted-foreground">{pkg.kind}</p>
                    {first && <span className="tag border-signal text-signal">First website</span>}
                  </div>
                  <p className="mt-8 text-sm text-muted-foreground">from</p>
                  <p className="title text-[clamp(2.3rem,3.4vw,3.2rem)]">
                    <span className="text-[0.62em] align-[0.28em]">₹</span>
                    {inr(pkg.priceInr)}
                  </p>
                  <p className="label mt-3 text-muted-foreground">
                    ${pkg.price} abroad · about {pkg.timelineDays} days
                  </p>
                  <ul className="mt-7 flex flex-col gap-2.5 text-sm leading-snug">
                    {pkg.deliverables.slice(0, 4).map((item) => (
                      <li key={item} className="flex gap-2.5">
                        <span aria-hidden className="mt-[0.45em] size-1.5 shrink-0 bg-signal" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-auto pt-9">
                    <Cta
                      href={wa ?? "/#contact"}
                      external={Boolean(wa)}
                      tone={first ? "signal" : "solid"}
                      className="w-full"
                    >
                      {wa ? "Ask on WhatsApp" : "Start a project"}
                    </Cta>
                  </div>
                </li>
              );
            })}
          </ul>
        </Fade>

        <Fade className="mt-8 flex flex-col gap-5 md:mt-10 md:flex-row md:items-center md:justify-between">
          <p className="max-w-2xl text-pretty text-muted-foreground">
            Websites for{" "}
            {niches.map((n, i) => (
              <span key={n.slug}>
                <a
                  href={`/websites-for/${n.slug}`}
                  className="text-foreground underline decoration-border underline-offset-4 transition-colors hover:decoration-signal"
                >
                  {n.plural.toLowerCase()}
                </a>
                {i < niches.length - 2 ? ", " : i === niches.length - 2 ? " and " : "."}
              </span>
            ))}
          </p>
          {bookingUrl && (
            <Cta href={bookingUrl} external tone="solid" className="min-w-52">
              Book a 15 minute call
            </Cta>
          )}
        </Fade>
      </div>
    </section>
  );
}
