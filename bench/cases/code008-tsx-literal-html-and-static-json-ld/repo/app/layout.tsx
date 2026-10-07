import type { ReactNode } from "react";
import { siteConfig } from "@/config/site";

const ORG_JSON_LD = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Acme Analytics",
  url: "https://acme.example",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  const site = { "@type": "WebSite", name: siteConfig.name, url: siteConfig.url };
  return (
    <html lang="en">
      <body>
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(ORG_JSON_LD) }} />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(site).replace(/</g, "\\u003c") }}
        />
        {children}
        <footer dangerouslySetInnerHTML={{ __html: "&copy; 2026 Acme Analytics &middot; All rights reserved" }} />
      </body>
    </html>
  );
}
