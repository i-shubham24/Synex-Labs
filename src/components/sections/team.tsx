import { team } from "@/data/content";
import { RollLink } from "../cta";
import { SNMark } from "../logo";
import { Fade, SectionHead } from "../reveal";

const STATES = ["s", "n"] as const;

export function Team() {
  return (
    <section id="team" className="surface-invert py-24 md:py-36">
      <div className="shell">
        <SectionHead
          index="05"
          label="Team"
          title={[
            <>
              <em>S</em> is Shubham.
            </>,
            <>
              <em>N</em> is Nitin.
            </>,
          ]}
          aside="Two developers, one studio. The same two people plan, design, build and support your project from the first call to launch."
        />

        <div className="mt-14 grid border-t border-l border-border md:mt-20 md:grid-cols-2">
          {team.map((person, i) => (
            <Fade key={person.name} delay={i * 0.12}>
              <article className="sn-trip group flex h-full flex-col gap-10 border-r border-b border-border p-6 transition-colors duration-500 hover:bg-card md:p-10">
                <div className="flex items-start justify-between gap-6">
                  <SNMark
                    state={STATES[i]}
                    className="w-[clamp(6rem,12vw,10.5rem)]"
                  />
                  <span className="tag">{person.role}</span>
                </div>

                <div className="flex flex-1 flex-col gap-4">
                  <h3 className="title text-[clamp(2.2rem,4vw,4rem)]">
                    {person.name}
                  </h3>
                  <p className="max-w-md text-lg leading-snug text-pretty">
                    {person.line}
                  </p>
                  <p className="flex flex-wrap gap-1.5 pt-2">
                    {person.skills.map((skill) => (
                      <span key={skill} className="tag">
                        {skill}
                      </span>
                    ))}
                  </p>
                </div>

                <div className="flex gap-6">
                  <RollLink
                    href={`https://github.com/${person.github}`}
                    external
                    className="label"
                  >
                    GitHub
                  </RollLink>
                  {person.linkedin && (
                    <RollLink href={person.linkedin} external className="label">
                      LinkedIn
                    </RollLink>
                  )}
                </div>
              </article>
            </Fade>
          ))}
        </div>
      </div>
    </section>
  );
}
