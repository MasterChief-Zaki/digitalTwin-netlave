import type { MetadataRoute } from "next";
import { isPreview, siteUrl } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: isPreview
      ? { userAgent: "*", disallow: "/" }
      : { userAgent: "*", allow: "/", disallow: "/api/" },
    ...(siteUrl && !isPreview
      ? { sitemap: new URL("/sitemap.xml", siteUrl).href }
      : {}),
  };
}
