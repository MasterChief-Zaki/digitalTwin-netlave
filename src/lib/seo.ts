import type { Metadata } from "next";
import truth from "@/content/ground-truth.json";

// Set the verified production origin at build time. Never invent a domain or
// canonicalize a production page to localhost / a temporary preview URL.
const configuredUrl = process.env.SITE_URL;
export const siteUrl = configuredUrl ? new URL(configuredUrl) : undefined;
if (
  siteUrl &&
  (!["https:", "http:"].includes(siteUrl.protocol) ||
    siteUrl.pathname !== "/" ||
    siteUrl.search ||
    siteUrl.hash)
) {
  throw new Error(
    "SITE_URL must be an absolute HTTP(S) origin without a path, query or fragment",
  );
}
export const isPreview = process.env.VERCEL_ENV === "preview";

export function pageMetadata(title: string, path: string): Metadata {
  const canonical = siteUrl ? new URL(path, siteUrl).href : undefined;
  const image = siteUrl
    ? new URL("/brand/social.png", siteUrl).href
    : undefined;
  return {
    title,
    description: truth.description,
    ...(siteUrl ? { metadataBase: siteUrl, alternates: { canonical } } : {}),
    applicationName: truth.brand,
    robots: { index: !isPreview, follow: !isPreview },
    openGraph: {
      title,
      description: truth.description,
      siteName: truth.brand,
      type: "website",
      locale: "en_US",
      ...(canonical ? { url: canonical } : {}),
      ...(image
        ? {
            images: [
              { url: image, width: 1200, height: 630, alt: truth.tagline },
            ],
          }
        : {}),
    },
    twitter: {
      card: "summary_large_image",
      title,
      description: truth.description,
      ...(image ? { images: [image] } : {}),
    },
  };
}
