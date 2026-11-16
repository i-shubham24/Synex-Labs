import type { MetadataRoute } from "next";
import { site } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/api/health", "/google-merchant.xml"],
        // /p/ holds private prospect previews made by the lead engine (also noindex per page)
        disallow: ["/api/contact", "/p/"],
      },
    ],
    sitemap: `${site.url}/sitemap.xml`,
    host: site.url,
  };
}
