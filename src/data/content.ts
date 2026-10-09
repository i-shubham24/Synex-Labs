export const services: {
  name: string;
  line: string;
  points: string[];
  // Project whose screens illustrate the service. Null shows the logo instead.
  project: string | null;
}[] = [
  {
    name: "Websites",
    line: "Company sites, landing pages and portfolios. Fast to load, clear to read and easy to update.",
    points: ["Design", "Copy structure", "SEO basics", "Hosting"],
    project: "zurich-estate",
  },
  {
    name: "Online stores",
    line: "Catalogue, cart, checkout and an admin panel you can run on your own.",
    points: ["Catalogue", "Checkout", "Payments", "Admin panel"],
    project: "aurex-truck-parts",
  },
  {
    name: "Web apps",
    line: "Dashboards, portals and platforms with logins, roles and real data behind them.",
    points: ["Accounts", "Database", "Dashboards", "Integrations"],
    project: "dolancer",
  },
  {
    name: "AI tools",
    line: "Scrapers, bots and AI helpers that take repeat work off your plate.",
    points: ["Scraping", "AI analysis", "Alerts", "Automation"],
    project: "ai-fb-scraper",
  },
  {
    name: "Mobile apps",
    line: "iOS and Android apps from one codebase, built with React Native.",
    points: ["React Native", "App Store", "Play Store", "Push alerts"],
    project: null,
  },
];

export const stack = [
  "React",
  "Next.js",
  "TypeScript",
  "Tailwind CSS",
  "Node.js",
  "Supabase",
  "PostgreSQL",
  "React Native",
  "Python",
  "AWS",
];

export const numbers = [
  { value: 13, label: "Projects built and in build" },
  { value: 3, label: "Countries we work with" },
  { value: 2, label: "People. No middlemen." },
];

export const reasons = [
  {
    name: "You talk to the builders",
    line: "No account managers. The people on the call are the people writing the code.",
  },
  {
    name: "A fixed quote up front",
    line: "You know the price and the timeline before any work starts.",
  },
  {
    name: "Progress you can click",
    line: "Every project runs on a live link, so you watch it grow week by week.",
  },
];

export const steps = [
  {
    name: "Talk",
    line: "A short call about your business, your goal and your budget. No sales pitch.",
  },
  {
    name: "Plan",
    line: "You get a fixed quote, a timeline and a clear list of what we will build.",
  },
  {
    name: "Build",
    line: "We design and code in the open. You watch it grow on a live link.",
  },
  {
    name: "Launch",
    line: "We test, deploy and hand over. Then we stay around for fixes and updates.",
  },
];

export const team = [
  {
    name: "Shubhampreet Singh",
    role: "Frontend and AI",
    line: "Designs the interface, builds the motion and adds the AI features.",
    skills: ["React", "Next.js", "Tailwind CSS", "Python", "Machine learning"],
    github: "i-shubham24",
    linkedin: "https://www.linkedin.com/in/shubhampreet-singh-12584824a",
  },
  {
    name: "Nitin Kumar",
    role: "Full stack and mobile",
    line: "Builds the backend, the APIs, the admin panels and the mobile apps.",
    skills: ["Node.js", "Next.js", "React Native", "PostgreSQL", "AWS"],
    github: "nitin612",
    linkedin: "",
  },
];

export const faqs = [
  {
    q: "How much does a website cost?",
    a: "It depends on the size. After a short call you get a fixed quote, so the price does not change halfway through.",
  },
  {
    q: "How long does it take?",
    a: "A landing page takes about a week. A full website takes two to four weeks. Stores and web apps take longer, and you get a timeline before we start.",
  },
  {
    q: "Do you work with clients outside India?",
    a: "Yes. We already work with clients in Switzerland and Australia, and we plan calls around your time zone.",
  },
  {
    q: "Who will I talk to?",
    a: "The two of us. You speak directly with the people who design and build your project.",
  },
  {
    q: "Can you fix or redesign my current site?",
    a: "Yes. We can redesign it, speed it up or rebuild it on a better stack.",
  },
  {
    q: "What happens after launch?",
    a: "We stay available for fixes, updates and new features. You also get the full code and every login.",
  },
];

// Who the studio builds for. Each card shows one matching project.
export const audiences = [
  {
    name: "Local businesses",
    line: "Shops, clinics and service firms that need a site that brings in enquiries.",
    needs: ["A clear page for each service", "Quote and booking forms", "Easy to find on Google"],
    project: "optimal-cleaning",
  },
  {
    name: "Online sellers",
    line: "Brands that want their own store, with a catalogue, a cart and a checkout.",
    needs: ["Product catalogue", "Cart and checkout", "An admin panel you can run"],
    project: "aurex-india",
  },
  {
    name: "Startups",
    line: "Founders who need a working product fast, without hiring a big team.",
    needs: ["A first version in weeks", "Logins, roles and real data", "Room to grow later"],
    project: "dolancer",
  },
  {
    name: "Agencies",
    line: "Teams that need a reliable build partner for their client work.",
    needs: ["Builds that match the design", "Clean handover", "Help when deadlines are tight"],
    project: "humble-solutions",
  },
];

export const about = [
  "Synex Labs is a web studio from India. We work with businesses here and abroad, from a broker in Zurich to a parts store in Australia.",
  "We stay small on purpose. No account managers and no handoffs. The two people on your first call are the two people who design, code and launch your project.",
];
