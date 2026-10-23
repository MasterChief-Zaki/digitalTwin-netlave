import type { Metadata } from "next";
import { ibmPlexMono, spaceGrotesk } from "@/styles/fonts";
import "./globals.scss";

export const metadata: Metadata = {
  title: "netLave Digital Twin",
  description:
    "A simulated digital twin of a self-powered, treated-wastewater irrigated forest.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${spaceGrotesk.variable} ${ibmPlexMono.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}
