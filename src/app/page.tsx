import { ProjectDialogProvider } from "@/components/project-dialog";
import { Audience } from "@/components/sections/audience";
import { Contact } from "@/components/sections/contact";
import { Faq } from "@/components/sections/faq";
import { Footer } from "@/components/sections/footer";
import { Hero } from "@/components/sections/hero";
import { Numbers } from "@/components/sections/numbers";
import { Process } from "@/components/sections/process";
import { Reel } from "@/components/sections/reel";
import { Services } from "@/components/sections/services";
import { Statement } from "@/components/sections/statement";
import { Team } from "@/components/sections/team";
import { Work } from "@/components/sections/work";
import { faqs } from "@/data/content";

// FAQ structured data belongs on the page that shows the FAQ.
const faqJsonLd = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: faqs.map((f) => ({
    "@type": "Question",
    name: f.q,
    acceptedAnswer: { "@type": "Answer", text: f.a },
  })),
};

export default function Home() {
  return (
    <ProjectDialogProvider>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(faqJsonLd).replace(/</g, "\\u003c"),
        }}
      />
      <main>
        <Hero />
        <Reel />
        <Statement />
        <Work />
        <Services />
        <Numbers />
        <Audience />
        <Process />
        <Team />
        <Faq />
        <Contact />
      </main>
      <Footer />
    </ProjectDialogProvider>
  );
}
