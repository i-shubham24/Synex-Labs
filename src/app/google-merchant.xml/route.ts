import { NextResponse } from "next/server";
import { servicePackages } from "@/data/packages";
import { site } from "@/lib/site";

function escapeXml(unsafe: string): string {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

export async function GET() {
  // Exclude any quote-only or zero-priced products from the Google Merchant feed.
  const eligibleProducts = servicePackages.filter((p) => p.price > 0);

  const itemsXml = eligibleProducts
    .map((product) => {
      const priceFormatted = `${product.price.toFixed(2)} ${product.currency}`;
      return `    <item>
      <g:id>${escapeXml(product.id)}</g:id>
      <g:title>${escapeXml(product.name)}</g:title>
      <g:description>${escapeXml(product.description)}</g:description>
      <g:link>${escapeXml(product.url)}</g:link>
      <g:image_link>${escapeXml(product.image)}</g:image_link>
      <g:availability>${product.availability}</g:availability>
      <g:price>${priceFormatted}</g:price>
      <g:brand>${escapeXml(product.brand)}</g:brand>
      <g:condition>${product.condition}</g:condition>
      <g:identifier_exists>no</g:identifier_exists>
      <g:mpn>${escapeXml(product.mpn)}</g:mpn>
      <g:product_type>${escapeXml(product.category)}</g:product_type>
      <g:shipping>
        <g:country>US</g:country>
        <g:service>Digital Delivery</g:service>
        <g:price>0.00 USD</g:price>
      </g:shipping>
      <g:shipping>
        <g:country>IN</g:country>
        <g:service>Digital Delivery</g:service>
        <g:price>0.00 INR</g:price>
      </g:shipping>
      <g:shipping>
        <g:country>AU</g:country>
        <g:service>Digital Delivery</g:service>
        <g:price>0.00 AUD</g:price>
      </g:shipping>
      <g:shipping>
        <g:country>CH</g:country>
        <g:service>Digital Delivery</g:service>
        <g:price>0.00 CHF</g:price>
      </g:shipping>
    </item>`;
    })
    .join("\n");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
  <channel>
    <title>${escapeXml(site.name)} - Products &amp; Services Feed</title>
    <link>${escapeXml(site.url)}</link>
    <description>${escapeXml(site.description)}</description>
${itemsXml}
  </channel>
</rss>`;

  return new NextResponse(xml, {
    status: 200,
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "public, max-age=86400, s-maxage=86400",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
