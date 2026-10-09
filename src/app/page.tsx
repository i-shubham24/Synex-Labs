import { ProjectDialogProvider } from "@/components/project-dialog";
import { Contact } from "@/components/sections/contact";
import { Faq } from "@/components/sections/faq";
import { Footer } from "@/components/sections/footer";
import { Hero } from "@/components/sections/hero";
import { Numbers } from "@/components/sections/numbers";
import { Process } from "@/components/sections/process";
import { Reel } from "@/components/sections/reel";
import { Services } from "@/components/sections/services";
import { Team } from "@/components/sections/team";
import { Work } from "@/components/sections/work";

export default function Home() {
  return (
    <ProjectDialogProvider>
      <main>
        <Hero />
        <Reel />
        <Work />
        <Services />
        <Numbers />
        <Process />
        <Team />
        <Faq />
        <Contact />
      </main>
      <Footer />
    </ProjectDialogProvider>
  );
}
