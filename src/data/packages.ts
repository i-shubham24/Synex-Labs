import { site } from "@/lib/site";

export type ServicePackage = {
  id: string;
  sku: string;
  mpn: string;
  name: string;
  kind: "Website" | "Online store" | "Web app" | "AI tool" | "Mobile app";
  summary: string;
  description: string;
  price: number; // in USD
  priceInr: number; // in INR
  currency: string;
  availability: "in_stock" | "out_of_stock" | "preorder";
  condition: "new";
  brand: string;
  category: string;
  deliverables: string[];
  timelineDays: number;
  url: string;
  image: string;
};

export const servicePackages: ServicePackage[] = [
  {
    id: "synex-starter-website",
    sku: "SYNEX-WEB-START",
    mpn: "SYNEX-WEB-01",
    name: "Starter Business Website Package",
    kind: "Website",
    summary: "A bespoke, lightning-fast company website or landing page with zero layout shift, rich SEO schemas, and contact integration.",
    description: "High-performance company website built with Next.js, TypeScript, and Tailwind CSS. Includes custom design, responsive layout, technical SEO with Schema.org JSON-LD, fast hosting setup, and enquiry form with spam protection.",
    price: 499,
    priceInr: 24999,
    currency: "USD",
    availability: "in_stock",
    condition: "new",
    brand: site.name,
    category: "Software > Computer Software",
    deliverables: [
      "Custom responsive design (Desktop & Mobile)",
      "Technical SEO & Structured Data (Schema.org)",
      "Lead capture form with honeypot & rate limiting",
      "Core Web Vitals 95+ score guarantee",
      "14 days post-launch warranty & handover",
    ],
    timelineDays: 7,
    url: `${site.url}/#services`,
    image: `${site.url}/opengraph-image`,
  },
  {
    id: "synex-ecommerce-store",
    sku: "SYNEX-STORE-PRO",
    mpn: "SYNEX-STORE-02",
    name: "E-Commerce Online Storefront",
    kind: "Online store",
    summary: "Modern e-commerce storefront with product catalogue, fast search, quote/checkout cart, and Stripe payment gateway.",
    description: "Full-stack online store designed for conversions. Features product catalogue with faceted filters, secure cart, payment gateway integration (Stripe, Razorpay, or custom), Google Merchant Center feed readiness, and custom admin management.",
    price: 999,
    priceInr: 49999,
    currency: "USD",
    availability: "in_stock",
    condition: "new",
    brand: site.name,
    category: "Software > Computer Software",
    deliverables: [
      "Complete product catalogue & category browsing",
      "Cart, checkout, and quote request workflow",
      "Stripe / Razorpay payment gateway integration",
      "Google Merchant Center XML product feed",
      "Self-serve admin panel for inventory & orders",
    ],
    timelineDays: 21,
    url: `${site.url}/#services`,
    image: `${site.url}/opengraph-image`,
  },
  {
    id: "synex-custom-webapp",
    sku: "SYNEX-APP-SAAS",
    mpn: "SYNEX-APP-03",
    name: "Custom Web Application & SaaS MVP",
    kind: "Web app",
    summary: "Production-ready web application with user authentication, database models, role-based dashboards, and REST/GraphQL APIs.",
    description: "Custom web app built with React, Next.js, Node.js, and PostgreSQL/Supabase. Features secure user accounts, RBAC, interactive dashboards, cloud storage, API integrations, and scalable serverless architecture.",
    price: 1499,
    priceInr: 79999,
    currency: "USD",
    availability: "in_stock",
    condition: "new",
    brand: site.name,
    category: "Software > Computer Software",
    deliverables: [
      "Zero-trust authentication & RBAC user roles",
      "Relational database schema & ORM migrations",
      "Interactive analytics & operations dashboard",
      "Protected REST endpoints with rate limiting",
      "CI/CD deployment pipeline on Vercel / AWS",
    ],
    timelineDays: 30,
    url: `${site.url}/#services`,
    image: `${site.url}/opengraph-image`,
  },
  {
    id: "synex-ai-automation",
    sku: "SYNEX-AI-TOOL",
    mpn: "SYNEX-AI-04",
    name: "AI Agent & Workflow Automation",
    kind: "AI tool",
    summary: "Custom AI pipeline with automated data ingestion, Gemini/LLM reasoning, structured data extraction, and Telegram alerts.",
    description: "Automated ingestion and intelligence engine. Monitors target channels, parses content via Google Gemini API, detects high-intent opportunities, filters noise, and dispatches real-time structured alerts to your private Telegram or Discord channel.",
    price: 799,
    priceInr: 39999,
    currency: "USD",
    availability: "in_stock",
    condition: "new",
    brand: site.name,
    category: "Software > Computer Software",
    deliverables: [
      "Safe multi-source ingestion & anti-bot scheduling",
      "Gemini AI reasoning & JSON extraction layer",
      "Local SQLite deduplication & state persistence",
      "Private Telegram Bot with inline action buttons",
      "Zero-cost cloud hosting setup instructions",
    ],
    timelineDays: 14,
    url: `${site.url}/#services`,
    image: `${site.url}/opengraph-image`,
  },
  {
    id: "synex-mobile-app",
    sku: "SYNEX-MOB-APP",
    mpn: "SYNEX-MOB-05",
    name: "Cross-Platform Mobile App (iOS & Android)",
    kind: "Mobile app",
    summary: "Single-codebase React Native mobile application for iOS and Android with offline caching, push alerts, and store readiness.",
    description: "Native-quality mobile application built using React Native and Expo. Integrates seamlessly with your backend API, supports offline state, secure token storage, native camera/location access, and full store preparation for Apple App Store and Google Play.",
    price: 1799,
    priceInr: 89999,
    currency: "USD",
    availability: "in_stock",
    condition: "new",
    brand: site.name,
    category: "Software > Computer Software",
    deliverables: [
      "Unified React Native / Expo codebase",
      "Native device hardware integration (biometrics, push)",
      "Offline state sync & Redux/Zustand state store",
      "App Store & Google Play metadata & screenshot assets",
      "Production store submission assistance",
    ],
    timelineDays: 35,
    url: `${site.url}/#services`,
    image: `${site.url}/opengraph-image`,
  },
];
