import type { MetadataRoute } from "next";

// Served at /f1-oracle/robots.txt because of basePath, AND at /robots.txt at
// the joeking.ai domain root via the next.config.ts rewrite.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: "https://joeking.ai/sitemap.xml",
    host: "https://joeking.ai",
  };
}
