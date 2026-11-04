import shots from "./shots.json";

export type Project = {
  slug: string;
  name: string;
  kind: "Website" | "Online store" | "Web app" | "AI tool" | "Mobile app";
  sector: string;
  place?: string;
  status: "Live" | "Completed" | "In build" | "Concept" | "On hold";
  summary: string;
  built: string[];
  stack: string[];
  url?: string;
  featured?: boolean;
  // Only the first frame is shown when the rest would expose private details.
  coverOnly?: boolean;
  // False when there is no phone capture to show.
  phone?: boolean;
  appStore?: string;
  playStore?: string;
};

export const projects: Project[] = [
  {
    slug: "almuna",
    name: "Al Muna Bookshop",
    kind: "Online store",
    sector: "Books and school supplies",
    place: "UAE and Oman",
    status: "On hold",
    summary:
      "An online school store for the UAE and Oman. Parents order textbooks, stationery and uniforms in one place.",
    built: ["Books, stationery and uniform shops", "Search and cart", "Sign up and account"],
    stack: ["React", "TypeScript"],
    url: "https://book-site-theta.vercel.app/",
  },
  {
    slug: "bliss-wedding",
    name: "The Bliss",
    kind: "Website",
    sector: "Wedding planning",
    place: "Amritsar, India",
    status: "In build",
    summary:
      "A site for a wedding planner in Amritsar. A 3D stack of bridal bangles opens the story, and every ceremony, wedding and review leads to one step: an enquiry.",
    built: ["3D bangle hero", "Ceremony and wedding pages", "Enquiry and WhatsApp flow"],
    stack: ["Next.js", "TypeScript", "Three.js", "GSAP"],
    url: "https://bliss-wedding.vercel.app",
  },
  {
    slug: "aditya-flexipack",
    name: "Aditya Flexipack",
    kind: "Website",
    sector: "Flexible packaging",
    place: "Kanpur, India",
    status: "In build",
    summary:
      "A site for a flexible packaging manufacturer in Kanpur. Six product lines, step-by-step factory stations and BRCGS credentials lead to one goal: a partner brief.",
    built: [
      "Product catalogue and packaging types",
      "Campus process stations",
      "B2B brief and sample inquiry",
    ],
    stack: ["Next.js", "TypeScript", "Tailwind CSS", "Motion"],
    url: "https://aditya-flexipack.vercel.app/",
  },
  {
    slug: "aurex-truck-parts",
    name: "Aurex Truck Parts",
    kind: "Online store",
    sector: "Truck and trailer parts",
    place: "Victoria, Australia",
    status: "Live",
    summary:
      "A parts store for Australian truck and trailer fleets. Buyers search by part number, build a quote cart and check out.",
    built: [
      "Catalogue with part number search",
      "Quote cart and checkout",
      "Admin dashboard and API",
    ],
    stack: ["React", "Vite", "Tailwind CSS", "Node.js"],
    url: "https://aurextruckparts.com.au/",
    featured: true,
  },
  {
    slug: "infini",
    name: "Infini",
    kind: "Website",
    sector: "Precision manufacturing",
    status: "Completed",
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
    name: "Dolancer",
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
    slug: "assignx",
    name: "AssignX",
    kind: "Web app",
    sector: "Managed work marketplace",
    status: "In build",
    summary:
      "A managed work marketplace. A client describes the task, a dedicated supervisor runs a vetted team, and payment stays in escrow until the work is approved.",
    built: [
      "Task posting and quotes",
      "Supervisor and milestone tracking",
      "Escrow payments",
    ],
    stack: ["React", "TypeScript", "Vite", "Tailwind CSS", "Framer Motion"],
    url: "https://assign-x-three.vercel.app",
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
    slug: "idael-alfonso",
    name: "Idael Alfonso",
    kind: "Website",
    sector: "Personal training",
    place: "Zurich, Switzerland",
    status: "In build",
    summary:
      "A site for a personal trainer and nutrition coach in Zurich. Walkthrough of private studio sessions, home visits and video training, leading to a free consultation.",
    built: [
      "Programme and session overview",
      "Training clips and credentials",
      "Free consultation booking",
    ],
    stack: ["React", "TypeScript", "Tailwind CSS", "Three.js"],
    url: "https://idael-olfonso.vercel.app/",
  },
  {
    slug: "vento-tea",
    name: "Vento Tea",
    kind: "Online store",
    sector: "Tea",
    place: "India",
    status: "On hold",
    summary:
      "A store for Assam and Darjeeling teas, with a scroll led home page and a full shopping flow.",
    built: ["Scroll led home page", "Cart and wishlist", "Coupons"],
    stack: ["React 19", "Vite", "Tailwind CSS", "Framer Motion"],
    phone: false,
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
    status: "Live",
    summary:
      "A scanner that watches marketplace listings, scores each deal with AI and sends price drop alerts on Telegram.",
    built: ["Live listing scanner", "AI deal and scam check", "Telegram alerts"],
    stack: ["Python", "Streamlit", "Gemini"],
    url: "https://fb-scraper-bot.streamlit.app/",
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

// Shown as a grid under the main list.
export const moreProjects: Project[] = [
  {
    slug: "dialysisongo",
    name: "DialysisOnGo",
    kind: "Web app",
    sector: "Healthcare",
    place: "India",
    status: "Live",
    summary:
      "A booking platform for dialysis patients across India. Find a vetted clinic, check free chairs and book a session, at home or while travelling.",
    built: ["Clinic search by distance", "Live chair availability", "Online booking"],
    stack: ["Next.js", "TypeScript", "Tailwind CSS", "AWS"],
    url: "https://dialysisongo.com/en",
  },
  {
    slug: "appy-saude",
    name: "Appy Saúde",
    kind: "Online store",
    sector: "Health marketplace",
    place: "Angola",
    status: "Live",
    summary:
      "A health marketplace and online pharmacy in Angola. Order medicine from partner pharmacies and book appointments online.",
    built: ["Pharmacy catalogue and orders", "Appointment booking", "Clinic and hospital directory"],
    stack: ["Next.js", "TypeScript", "Redux Toolkit", "AWS"],
    url: "https://www.appysaude.co.ao/en",
  },
  {
    slug: "tracevenue",
    name: "TraceVenue",
    kind: "Web app",
    sector: "Events and venues",
    status: "Live",
    summary:
      "A marketplace that connects event planners with venues, banquet halls and caterers, with quote requests and side by side comparison.",
    built: ["Venue search", "Quote requests", "Amenity comparison"],
    stack: ["JavaScript", "REST APIs", "Tailwind CSS"],
    url: "https://tracevenue.com/",
  },
  {
    slug: "vitalwatch-365",
    name: "VitalWatch 365",
    kind: "Web app",
    sector: "Remote patient care",
    place: "USA",
    status: "Live",
    summary:
      "A remote patient monitoring platform. Patients follow guided physical therapy with AI pose tracking, and clinicians see vitals from connected medical devices.",
    built: ["AI therapy trainer", "Exercise library", "Clinician alerts"],
    stack: ["React", "TensorFlow.js", "MediaPipe", "AWS"],
    phone: false,
  },
  {
    slug: "pixory",
    name: "Pixory",
    kind: "Online store",
    sector: "Photobooks",
    place: "UK",
    status: "Live",
    summary:
      "A photobook studio where customers lay out their own hardcover book in the browser and order it.",
    built: ["Live book editor", "Automatic photo layout", "Stripe checkout"],
    stack: ["Next.js", "TypeScript", "Canvas API", "Stripe"],
    url: "https://www.pixoryofficial.com/",
  },
  {
    slug: "browserbase",
    name: "Browserbase",
    kind: "Web app",
    sector: "AI infrastructure",
    place: "USA",
    status: "Live",
    summary:
      "A cloud platform that runs headless browsers for AI agents, with browser sandboxes and live session replay.",
    built: ["Browser sandboxes", "Session replay", "Agent framework"],
    stack: ["TypeScript", "Playwright", "Puppeteer"],
    url: "https://www.browserbase.com/",
  },
  {
    slug: "fadega",
    name: "Fadega",
    kind: "Online store",
    sector: "Marketplace",
    status: "In build",
    summary:
      "A multi vendor marketplace now in development, with product search, category filters and order handling.",
    built: ["Multi vendor catalogue", "Search and filters", "Cart and orders"],
    stack: ["Next.js", "TypeScript", "PostgreSQL", "AWS"],
    phone: false,
  },
  // Mobile apps. Their frames are boards of real app screens, not site captures.
  {
    slug: "appy-saude-app",
    name: "Appy Saúde app",
    kind: "Mobile app",
    sector: "Pharmacy and health",
    place: "Angola",
    status: "Live",
    summary:
      "The Appy Saúde app for iOS and Android. People across Angola order medicine, pay in kwanza and find a pharmacy or clinic near them.",
    built: ["Medicine orders and payment", "Pharmacy and clinic finder", "Portuguese and English"],
    stack: ["React Native", "Expo", "Redux Toolkit", "AWS"],
    appStore: "https://apps.apple.com/us/app/appy-sa%C3%BAde/id1220393420",
    playStore: "https://play.google.com/store/apps/details?id=ao.co.appy.saude",
  },
  {
    slug: "vitalwatch-365-app",
    name: "VitalWatch 365 app",
    kind: "Mobile app",
    sector: "Remote patient care",
    place: "USA",
    status: "Live",
    summary:
      "The patient app for VitalWatch 365. It syncs vitals from Bluetooth medical devices and walks patients through their therapy plan.",
    built: ["Bluetooth device sync", "Therapy plans and exercise library", "Health surveys and reminders"],
    stack: ["React Native", "TanStack Query", "Bluetooth LE", "AWS"],
    appStore: "https://apps.apple.com/us/app/vital-watch-365/id6475680352",
    playStore: "https://play.google.com/store/apps/details?id=com.vitalwatch365.app",
  },
  {
    slug: "fujima",
    name: "Fujima",
    kind: "Mobile app",
    sector: "Wholesale ordering",
    place: "USA",
    status: "Live",
    summary:
      "A trade ordering app for Fujima, a wholesale supplier of smoking accessories. Business customers browse the catalogue, search by barcode and place orders from their phone.",
    built: ["Catalogue by category", "Barcode search", "Cart and ordering"],
    stack: ["React Native", "Expo"],
    appStore: "https://apps.apple.com/us/app/fujima/id6479015935",
    phone: false,
  },
];

export const allProjects = [...projects, ...moreProjects];
