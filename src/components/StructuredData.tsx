import truth from "@/content/ground-truth.json";
import { siteUrl } from "@/lib/seo";

export function StructuredData() {
  const graph = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: truth.brand,
    description: truth.description,
    inLanguage: "en",
    ...(siteUrl ? { url: siteUrl.href } : {}),
    about: {
      "@type": "Thing",
      name: "NetLave treated-wastewater forestry simulation prototype",
      description: `${truth.claimLimit} ${truth.controllerStatus}`,
      sameAs: truth.source.repository,
    },
  };
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify(graph).replace(/</g, "\\u003c"),
      }}
    />
  );
}
