// One place for the studio details. Change these and the whole site follows.
export const site = {
  name: "Synex Labs",
  title: "Synex Labs | Websites, online stores and web apps",
  description:
    "Synex Labs is a two person studio. We design and build websites, online stores, web apps and AI tools for businesses in India, Switzerland, Australia and the UAE.",
  email: "shubhamkaler24@gmail.com",
  base: "India",
  timeZone: "Asia/Kolkata",
  // Canonical production URL (Cloudflare Pages). Override with NEXT_PUBLIC_SITE_URL when
  // a custom domain is connected. Note: synexlabs.in belongs to a different company.
  url:
    process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ||
    "https://synex-labs.pages.dev",
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
  // Rooted at "/" so they also work from a project page.
  nav: [
    { label: "Work", href: "/#work" },
    { label: "Services", href: "/#services" },
    { label: "Process", href: "/#process" },
    { label: "Team", href: "/#team" },
    { label: "FAQ", href: "/#faq" },
  ],
};
