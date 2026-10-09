import { Plus } from "lucide-react";
import { faqs } from "@/data/content";
import { Label, Rise } from "../reveal";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "../ui/accordion";

export function Faq() {
  return (
    <section id="faq" className="py-24 md:py-36">
      <div className="shell">
        <Label index="07">FAQ</Label>

        <div className="mt-8 grid grid-cols-12 gap-x-8 gap-y-10 md:mt-12">
          <div className="col-span-12 lg:col-span-5">
            <h2 className="title text-[clamp(2.6rem,6.3vw,6.4rem)] lg:sticky lg:top-28">
              <Rise>Good to</Rise>
              <Rise delay={0.08}>
                <i>know.</i>
              </Rise>
            </h2>
          </div>

          <Accordion
            type="single"
            collapsible
            defaultValue="item-0"
            className="col-span-12 border-t border-border lg:col-span-7"
          >
            {faqs.map((item, i) => (
              <AccordionItem
                key={item.q}
                value={`item-${i}`}
                className="border-b border-border"
              >
                <AccordionTrigger className="group items-center gap-6 rounded-none py-6 text-left hover:no-underline md:py-7 [&>[data-slot=accordion-trigger-icon]]:hidden">
                  <span className="flex items-baseline gap-5">
                    <span className="label text-muted-foreground group-aria-expanded:text-signal">
                      0{i + 1}
                    </span>
                    <span className="title text-xl md:text-[1.65rem]">
                      {item.q}
                    </span>
                  </span>
                  <span className="grid size-9 shrink-0 place-items-center bg-foreground/10 transition-colors duration-300 group-hover:bg-signal group-hover:text-[#11110f] group-aria-expanded:bg-signal group-aria-expanded:text-[#11110f]">
                    <Plus className="size-4 transition-transform duration-300 group-aria-expanded:rotate-45" />
                  </span>
                </AccordionTrigger>
                <AccordionContent className="max-w-2xl pr-12 pb-7 pl-[2.4rem] text-lg leading-snug text-pretty text-muted-foreground">
                  {item.a}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </div>
    </section>
  );
}
