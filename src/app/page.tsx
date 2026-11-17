import { ProjectDialogProvider } from "@/components/project-dialog";
import { Audience } from "@/components/sections/audience";
import { Contact } from "@/components/sections/contact";
import { Faq } from "@/components/sections/faq";
import { Footer } from "@/components/sections/footer";
import { Hero } from "@/components/sections/hero";
import { Numbers } from "@/components/sections/numbers";
import { Pricing } from "@/components/sections/pricing";
import { Process } from "@/components/sections/process";
import { Reel } from "@/components/sections/reel";
import { Services } from "@/components/sections/services";
import { Statement } from "@/components/sections/statement";
import { Team } from "@/components/sections/team";
import { Work } from "@/components/sections/work";
import { faqs } from "@/data/content";
import { allProjects } from "@/data/projects";
import { site } from "@/lib/site";

// 1. FAQPage Schema for Search Engine Rich Snippets
const faqJsonLd = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: faqs.map((f) => ({
    "@type": "Question",
    name: f.q,
    acceptedAnswer: { "@type": "Answer", text: f.a },
  })),
};

// 2. Local Business / Professional Service Schema with full footprint
const professionalServiceJsonLd = {
  "@context": "https://schema.org",
  "@type": "ProfessionalService",
  "@id": `${site.url}/#professionalservice`,
  name: site.name,
  legalName: site.name,
  url: site.url,
  description: site.description,
  image: `${site.url}/opengraph-image`,
  logo: `${site.url}/apple-icon.png`,
  email: site.email,
  priceRange: "$$",
  currenciesAccepted: "INR, USD, CHF, AUD, AED",
  paymentAccepted: "Bank Transfer, UPI, Stripe, Wire Transfer",
  address: {
    "@type": "PostalAddress",
    addressLocality: "Amritsar",
    addressRegion: "Punjab",
    addressCountry: "IN",
  },
  geo: {
    "@type": "GeoCoordinates",
    latitude: 31.634,
    longitude: 74.8723,
  },
  openingHoursSpecification: [
    {
      "@type": "OpeningHoursSpecification",
      dayOfWeek: [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
      ],
      opens: "09:00",
      closes: "20:00",
    },
  ],
  areaServed: ["IN", "CH", "AU", "AE", "US", "GB"],
};

// 3. ItemList Schema indexing all portfolio case studies
const projectListJsonLd = {
  "@context": "https://schema.org",
  "@type": "ItemList",
  name: "Synex Labs Portfolio & Case Studies",
  description: "Selected websites, online stores, web apps and AI tools built by Synex Labs.",
  itemListElement: allProjects.map((project, idx) => ({
    "@type": "ListItem",
    position: idx + 1,
    name: project.name,
    url: `${site.url}/work/${project.slug}`,
    description: project.summary,
    image: `${site.url}/work/${project.slug}/desktop-1.webp`,
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
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(professionalServiceJsonLd).replace(/</g, "\\u003c"),
        }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(projectListJsonLd).replace(/</g, "\\u003c"),
        }}
      />
      <main>
        <Hero />
        <Reel />
        <Statement />
        <Work />
        <Services />
        <Pricing />
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
