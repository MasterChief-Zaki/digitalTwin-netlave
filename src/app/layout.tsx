import { StructuredData } from "@/components/StructuredData";
import { pageMetadata } from "@/lib/seo";
import { ibmPlexMono, spaceGrotesk } from "@/styles/fonts";
import "./globals.scss";

export const metadata = pageMetadata(
  "NetLave Digital Twin — TSE irrigation simulation dashboard",
  "/",
);

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${spaceGrotesk.variable} ${ibmPlexMono.variable}`}
    >
      <body>
        <StructuredData />
        {children}
      </body>
    </html>
  );
}
