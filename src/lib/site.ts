// One place for the studio details. Change these and the whole site follows.
export const site = {
  name: "Synex Labs",
  title: "Synex Labs | Websites, online stores and web apps",
  description:
    "Synex Labs is a two person studio. We design and build websites, online stores, web apps and AI tools for businesses in India, Switzerland and Australia.",
  email: "shubhamkaler24@gmail.com",
  base: "India",
  timeZone: "Asia/Kolkata",
  // Canonical production URL. Override with SITE_URL env in preview/prod.
  url:
    process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ||
    "https://synexlabs.in",
  locale: "en_IN",
  twitterHandle: "@synexlabs",
  keywords: [
    "web studio India",
    "website design",
    "online store development",
    "web app development",
    "Next.js agency",
    "React Native apps",
    "AI tools",
  ],
  authors: [
    { name: "Shubhampreet Singh" },
    { name: "Nitin Kumar" },
  ],
  nav: [
    { label: "Work", href: "#work" },
    { label: "Services", href: "#services" },
    { label: "Process", href: "#process" },
    { label: "Team", href: "#team" },
    { label: "FAQ", href: "#faq" },
  ],
};
