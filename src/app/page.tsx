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

export default function Home() {
  return (
    <ProjectDialogProvider>
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
