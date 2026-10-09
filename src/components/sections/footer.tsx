import { site } from "@/lib/site";
import { RollLink } from "../cta";
import { EmailLink } from "../email";
import { Kinetic } from "../kinetic";
import { SNLogo } from "../logo";

export function Footer() {
  return (
    <footer className="surface-invert overflow-x-clip pt-16 pb-8 md:pt-24">
      <div className="shell">
        <div className="grid grid-cols-12 gap-x-8 gap-y-10">
          <div className="col-span-12 flex flex-col gap-5 md:col-span-6">
            <SNLogo className="text-6xl md:text-7xl" />
            <p className="max-w-sm text-lg leading-snug text-pretty">
              A two person studio for websites, online stores, web apps and AI
              tools.
            </p>
          </div>

          <nav
            aria-label="Footer"
            className="label col-span-6 flex flex-col items-start gap-3 md:col-span-3"
          >
            {[...site.nav, { label: "Contact", href: "#contact" }].map((item) => (
              <RollLink key={item.href} href={item.href}>
                {item.label}
              </RollLink>
            ))}
          </nav>

          <div className="label col-span-6 flex flex-col items-start gap-3 md:col-span-3">
            <EmailLink label="Email" />
            <RollLink href="https://github.com/i-shubham24" external>
              GitHub / Shubham
            </RollLink>
            <RollLink href="https://github.com/nitin612" external>
              GitHub / Nitin
            </RollLink>
          </div>
        </div>

        <p className="display mt-14 text-[19.4vw] leading-[0.8] select-none md:mt-20 min-[1680px]:text-[20.2rem]">
          <Kinetic text="Synex Labs" rest={62} peak={104} radius={320} className="[font-stretch:62%]" />
        </p>

        <div className="label mt-6 flex flex-wrap justify-between gap-3 text-muted-foreground">
          <span>2026 Synex Labs</span>
          <RollLink href="#top">Back to top</RollLink>
        </div>
      </div>
    </footer>
  );
}
