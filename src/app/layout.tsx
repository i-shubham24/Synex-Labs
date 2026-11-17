import { Analytics } from "@vercel/analytics/next";
import type { Metadata, Viewport } from "next";
import { Archivo, Geist_Mono } from "next/font/google";
import { Cursor } from "@/components/cursor";
import { Nav } from "@/components/nav";
import { Preloader } from "@/components/preloader";
import { Providers } from "@/components/providers";
import { themeScript } from "@/components/theme-toggle";
import { WhatsAppButton } from "@/components/whatsapp-button";
import { services } from "@/data/content";
import { allProjects } from "@/data/projects";
import { servicePackages } from "@/data/packages";
import { site } from "@/lib/site";
import "./globals.css";

const archivo = Archivo({
  variable: "--font-archivo",
  subsets: ["latin"],
  axes: ["wdth"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f2efe8" },
    { media: "(prefers-color-scheme: dark)", color: "#0e0e0c" },
  ],
};

export const metadata: Metadata = {
  metadataBase: new URL(site.url),
  title: {
    default: site.title,
    template: "%s | Synex Labs",
  },
  description: site.description,
  keywords: site.keywords,
  authors: site.authors,
  creator: site.name,
  publisher: site.name,
  alternates: { canonical: "/" },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  openGraph: {
    type: "website",
    locale: site.locale,
    url: "/",
    siteName: site.name,
    title: site.title,
    description: site.description,
    images: [
      {
        url: "/opengraph-image",
        width: 1200,
        height: 630,
        alt: "Synex Labs. Websites that win you clients.",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: site.title,
    description: site.description,
    images: [
      { url: "/twitter-image", alt: "Synex Labs. Websites that win you clients." },
    ],
    creator: site.twitterHandle,
  },
  icons: { icon: "/icon.svg", apple: "/apple-icon.png" },
  manifest: "/manifest.webmanifest",
  category: "technology",
  // Search Console ownership tag, when its token is configured.
  ...(process.env.GOOGLE_SITE_VERIFICATION && {
    verification: { google: process.env.GOOGLE_SITE_VERIFICATION },
  }),
};

const organizationJsonLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: site.name,
  legalName: site.name,
  url: site.url,
  description: site.description,
  image: `${site.url}/opengraph-image`,
  logo: `${site.url}/apple-icon.png`,
  email: site.email,
  foundingDate: "2024",
  founders: [
    {
      "@type": "Person",
      name: "Shubhampreet Singh",
      jobTitle: "Co-Founder & Lead Frontend / AI",
      sameAs: "https://www.linkedin.com/in/shubhampreet-singh-12584824a",
    },
    {
      "@type": "Person",
      name: "Nitin Kumar",
      jobTitle: "Co-Founder & Lead Backend / Mobile",
      sameAs: "https://github.com/nitin612",
    },
  ],
  address: {
    "@type": "PostalAddress",
    addressLocality: "Amritsar",
    addressRegion: "Punjab",
    addressCountry: "IN",
  },
  areaServed: ["IN", "CH", "AU", "AE", "US", "GB"],
  sameAs: [
    "https://github.com/i-shubham24",
    "https://github.com/nitin612",
    "https://www.linkedin.com/in/shubhampreet-singh-12584824a",
  ],
  contactPoint: {
    "@type": "ContactPoint",
    contactType: "project enquiries",
    url: `${site.url}/#contact`,
    email: site.email,
    availableLanguage: ["English", "Hindi", "Punjabi"],
  },
  hasOfferCatalog: {
    "@type": "OfferCatalog",
    name: "Synex Labs Services and Packages",
    itemListElement: [
      ...services.map((s, i) => ({
        "@type": "Offer",
        position: i + 1,
        itemOffered: { "@type": "Service", name: s.name, description: s.line },
      })),
      ...servicePackages.map((pkg, i) => ({
        "@type": "Offer",
        position: services.length + i + 1,
        itemOffered: {
          "@type": "Product",
          name: pkg.name,
          description: pkg.description,
          sku: pkg.sku,
          offers: {
            "@type": "Offer",
            price: pkg.price,
            priceCurrency: pkg.currency,
            availability: "https://schema.org/InStock",
            url: pkg.url,
          },
        },
      })),
    ],
  },
};

const websiteJsonLd = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: site.name,
  alternateName: "SynexLabs",
  url: site.url,
  description: site.description,
  inLanguage: "en",
  publisher: {
    "@type": "Organization",
    name: site.name,
    url: site.url,
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-theme="light"
      data-scroll-behavior="smooth"
      suppressHydrationWarning
      className={`${archivo.variable} ${geistMono.variable} antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        {/* Structured data: `<` escaped to block HTML injection */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(organizationJsonLd).replace(/</g, "\\u003c"),
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(websiteJsonLd).replace(/</g, "\\u003c"),
          }}
        />
      </head>
      <body className="min-h-svh">
        {/* Crawler-ready noscript fallback: ensures search bots without JS index all routes and content */}
        <noscript>
          <div style={{ padding: "2rem", background: "#f2efe8", color: "#11110f", fontFamily: "sans-serif" }}>
            <h1>Synex Labs | Websites, online stores and web apps</h1>
            <p>Synex Labs is a technical duo studio building custom websites, web apps, online stores, and AI tools for businesses across India, Switzerland, Australia, and the UAE.</p>
            
            <h2>Our Services</h2>
            <ul>
              {services.map((s) => (
                <li key={s.name}>
                  <strong>{s.name}</strong>: {s.line}
                </li>
              ))}
            </ul>

            <h2>Selected Client Work &amp; Case Studies</h2>
            <ul>
              {allProjects.map((p) => (
                <li key={p.slug}>
                  <a href={`/work/${p.slug}`}>
                    <strong>{p.name}</strong> - {p.kind} ({p.sector}{p.place ? `, ${p.place}` : ""})
                  </a>
                  <p>{p.summary}</p>
                </li>
              ))}
            </ul>

            <h2>Contact Us</h2>
            <p>Email: <a href={`mailto:${site.email}`}>{site.email}</a></p>
          </div>
        </noscript>

        <Providers>
          <Preloader />
          <Nav />
          {children}
          <WhatsAppButton />
          <Cursor />
        </Providers>
        {process.env.VERCEL && <Analytics />}
        <div aria-hidden className="grain" />
      </body>
    </html>
  );
}
