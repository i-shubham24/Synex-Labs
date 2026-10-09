import { about } from "@/data/content";
import { SNMark } from "../logo";
import { Fade } from "../reveal";

const TEXT =
  "We are Shubham and Nitin. Two developers who plan, design and build your project ourselves, from the first call to launch.";
const ACCENT = new Set(["Shubham", "Nitin."]);

// The studio in one sentence, held between its two letters.
// The letters turn and the words light up as the block scrolls past.
export function Statement() {
  return (
    <section
      aria-label="About the studio"
      className="surface-invert py-20 md:py-32"
    >
      <div className="shell">
        <div className="grid grid-cols-12 items-center gap-x-8 gap-y-10">
          <div className="sn-trip col-span-4 col-start-2 max-w-36 lg:col-span-2 lg:col-start-1 lg:max-w-none">
            <SNMark state="s" className="scroll-spin" title="The letter S" />
          </div>
          <div className="sn-trip col-span-4 col-start-8 max-w-36 justify-self-end lg:order-3 lg:col-span-2 lg:col-start-11 lg:max-w-none lg:justify-self-auto">
            <SNMark
              state="n"
              className="scroll-spin-back"
              title="The letter N"
            />
          </div>
          <p className="words title col-span-12 text-center text-[clamp(1.7rem,3.6vw,3.5rem)] leading-[1.08] text-balance lg:order-2 lg:col-span-8">
            {TEXT.split(" ").map((word, i) => (
              <span
                key={i}
                className={ACCENT.has(word) ? "word text-signal" : "word"}
                style={{ "--i": i } as React.CSSProperties}
              >
                {word}{" "}
              </span>
            ))}
          </p>
        </div>

        <div className="mt-20 grid grid-cols-12 gap-x-8 gap-y-8 md:mt-28">
          <Fade className="col-span-12 lg:col-span-3">
            <span className="tag border-transparent bg-foreground/10">
              Who we are
            </span>
          </Fade>
          <div className="col-span-12 flex flex-col gap-5 lg:col-span-6">
            {about.map((text, i) => (
              <Fade key={i} delay={i * 0.1}>
                <p className="text-lg leading-snug text-pretty md:text-xl">
                  {text}
                </p>
              </Fade>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
