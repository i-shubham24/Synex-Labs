import { Analytics } from "@vercel/analytics/next";
import type { Metadata, Viewport } from "next";
import { Archivo, Geist_Mono } from "next/font/google";
import { Cursor } from "@/components/cursor";
import { Nav } from "@/components/nav";
import { Preloader } from "@/components/preloader";
import { Providers } from "@/components/providers";
import { themeScript } from "@/components/theme-toggle";
import { services } from "@/data/content";
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
  url: site.url,
  description: site.description,
  image: `${site.url}/opengraph-image`,
  logo: `${site.url}/apple-icon.png`,
  address: { "@type": "PostalAddress", addressCountry: "IN" },
  areaServed: ["IN", "CH", "AU", "AE"],
  sameAs: [
    "https://github.com/i-shubham24",
    "https://github.com/nitin612",
  ],
  contactPoint: {
    "@type": "ContactPoint",
    contactType: "project enquiries",
    url: `${site.url}/#contact`,
    availableLanguage: "English",
  },
  hasOfferCatalog: {
    "@type": "OfferCatalog",
    name: "What Synex Labs builds",
    itemListElement: services.map((s, i) => ({
      "@type": "Offer",
      position: i + 1,
      itemOffered: { "@type": "Service", name: s.name, description: s.line },
    })),
  },
};

const websiteJsonLd = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: site.name,
  url: site.url,
  description: site.description,
  inLanguage: "en",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-theme="light"
      // Anchor links glide, but moving between pages jumps straight to the top.
      data-scroll-behavior="smooth"
      suppressHydrationWarning
      className={`${archivo.variable} ${geistMono.variable} antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        {/* Structured data. `<` is escaped per Next.js JSON-LD guidance to block XSS. */}
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
        <Providers>
          <Preloader />
          <Nav />
          {children}
          <Cursor />
        </Providers>
        {/* Cookie-free page views. Only on Vercel, which serves the script
            from this same origin, so the CSP needs no new source. */}
        {process.env.VERCEL && <Analytics />}
        <div aria-hidden className="grain" />
      </body>
    </html>
  );
}
