import shots from "./shots.json";

export type Project = {
  slug: string;
  name: string;
  kind: "Website" | "Online store" | "Web app" | "AI tool";
  sector: string;
  place?: string;
  status: "Live" | "In build" | "Concept";
  summary: string;
  built: string[];
  stack: string[];
  url?: string;
  featured?: boolean;
  // Only the first frame is shown when the rest would expose private details.
  coverOnly?: boolean;
};

export const projects: Project[] = [
  {
    slug: "zurich-estate",
    name: "Optimal Immobilien",
    kind: "Website",
    sector: "Real estate",
    place: "Zurich, Switzerland",
    status: "Live",
    summary:
      "A site for a Zurich broker who sells homes at a fixed price. Every page leads to one thing: a free property valuation.",
    built: [
      "Property valuation funnel",
      "Scroll animations",
      "Custom design system",
    ],
    stack: ["Next.js", "TypeScript"],
    url: "https://optimal-immobilien.ch/",
    featured: true,
  },
  {
    slug: "aurex-truck-parts",
    name: "Aurex Truck Parts",
    kind: "Online store",
    sector: "Truck and trailer parts",
    place: "Victoria, Australia",
    status: "In build",
    summary:
      "A parts store for Australian truck and trailer fleets. Buyers search by part number, build a quote cart and check out.",
    built: [
      "Catalogue with part number search",
      "Quote cart and checkout",
      "Admin dashboard and API",
    ],
    stack: ["React", "Vite", "Tailwind CSS", "Node.js"],
    url: "https://aurex-trucks-parts.vercel.app",
    featured: true,
  },
  {
    slug: "infini",
    name: "Infini",
    kind: "Website",
    sector: "Precision manufacturing",
    status: "In build",
    summary:
      "A company site for a surface finishing firm. It explains a technical process in plain steps and points engineers to one action: send a part.",
    built: [
      "Capability and industry pages",
      "Case studies and certifications",
      "News and events",
    ],
    stack: ["React"],
    url: "https://infini-three.vercel.app",
    featured: true,
  },
  {
    slug: "dolancer",
    name: "Dolancer by AssignX",
    kind: "Web app",
    sector: "Work platform",
    place: "India",
    status: "In build",
    summary:
      "A platform where vetted specialists get fixed price tasks from a supervisor. No bidding and no client calls.",
    built: [
      "Task offers with fixed pay",
      "Supervisor review flow",
      "Payouts to bank and UPI",
    ],
    stack: ["React 19", "TypeScript", "Supabase", "TanStack Query"],
    url: "https://dolancer.vercel.app",
    featured: true,
  },
  {
    slug: "aurex-india",
    name: "Aurex India",
    kind: "Online store",
    sector: "Cookware",
    place: "India",
    status: "Live",
    summary:
      "A store for triply steel and cast iron cookware, with sign in by mobile OTP and free shipping across India.",
    built: ["Product collections", "Mobile OTP sign in", "Offers and checkout"],
    stack: [],
    url: "https://www.aurexindia.com/",
  },
  {
    slug: "optimal-cleaning",
    name: "Optimal Reinigung",
    kind: "Website",
    sector: "Cleaning services",
    place: "Zurich, Switzerland",
    status: "In build",
    summary:
      "A German language site for a Swiss cleaning company. Fixed prices up front and a short path to a quote.",
    built: ["Services and pricing", "Quote request flow", "German content"],
    stack: ["React"],
    url: "https://optimal-cleaning-eta.vercel.app",
  },
  {
    slug: "fieldofsoma",
    name: "Field of Soma",
    kind: "Website",
    sector: "Movement and wellness",
    status: "In build",
    summary:
      "A calm site for a movement and somatic education practice, with session booking and a member login.",
    built: ["Practice pages", "Session booking", "Member login"],
    stack: ["React"],
    url: "https://fieldofsoma.vercel.app",
  },
  {
    slug: "humble-solutions",
    name: "Humble Solutions",
    kind: "Website",
    sector: "Software studio",
    place: "India",
    status: "Live",
    summary:
      "A portfolio for a digital product studio. Seven scroll chapters walk through clients, work and results.",
    built: ["Chapter based scroll", "Client and project showcase", "Contact"],
    stack: [],
    url: "https://portfolio.humblesolutions.in/",
  },
  {
    slug: "eve-pizzeria",
    name: "Eve's Pizzeria",
    kind: "Online store",
    sector: "Food ordering",
    place: "Victoria, Australia",
    status: "Concept",
    summary:
      "An ordering site for a halal pizzeria. Menu, pizza builder, deals, cart and checkout.",
    built: ["Interactive menu", "Pizza builder", "Cart and checkout"],
    stack: ["React", "TypeScript", "Tailwind CSS", "GSAP"],
    url: "https://eve-pizzeria.vercel.app",
  },
  {
    slug: "invitation-cards",
    name: "Wedding Invitation",
    kind: "Website",
    sector: "Events",
    place: "India",
    status: "Live",
    summary:
      "A wedding invitation that opens like an envelope, with a live countdown, music and RSVP.",
    built: ["Envelope opening", "Countdown and music", "RSVP and guestbook"],
    stack: ["React", "Supabase"],
    coverOnly: true,
  },
  {
    slug: "ai-fb-scraper",
    name: "AI Deal Scanner",
    kind: "AI tool",
    sector: "Marketplace automation",
    status: "In build",
    summary:
      "A scanner that watches marketplace listings, scores each deal with AI and sends price drop alerts on Telegram.",
    built: ["Live listing scanner", "AI deal and scam check", "Telegram alerts"],
    stack: ["Python", "Streamlit", "Gemini"],
  },
];

const frameCount = shots as Record<string, number>;

export function frames(project: Project): string[] {
  const count = project.coverOnly ? 1 : (frameCount[project.slug] ?? 1);
  return Array.from(
    { length: Math.max(1, count) },
    (_, i) => `/work/${project.slug}/desktop-${i + 1}.webp`,
  );
}

export const cover = (project: Project) =>
  `/work/${project.slug}/desktop-1.webp`;
export const mobileShot = (project: Project) =>
  `/work/${project.slug}/mobile.webp`;

export const featured = projects.filter((p) => p.featured);
export const more = projects.filter((p) => !p.featured);
