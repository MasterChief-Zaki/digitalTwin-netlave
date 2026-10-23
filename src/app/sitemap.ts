import type { MetadataRoute } from "next";
import { isPreview, siteUrl } from "@/lib/seo";

export default function sitemap(): MetadataRoute.Sitemap {
  if (!siteUrl || isPreview) return [];
  return ["/", "/ground-truth"].map((path) => ({
    url: new URL(path, siteUrl).href,
  }));
}
