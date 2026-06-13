import type { MetadataRoute } from "next";

// Static sitemap for the F1 Oracle surface. Lists the 3 user-facing routes
// plus root. URLs use the canonical joeking.ai/f1-oracle prefix.
export default function sitemap(): MetadataRoute.Sitemap {
  const base = "https://joeking.ai/f1-oracle";
  const now = new Date();
  return [
    { url: `${base}/`,          lastModified: now, changeFrequency: "hourly", priority: 1.0 },
    { url: `${base}/race`,      lastModified: now, changeFrequency: "hourly", priority: 0.9 },
    { url: `${base}/portfolio`, lastModified: now, changeFrequency: "daily",  priority: 0.8 },
    { url: `${base}/record`,    lastModified: now, changeFrequency: "daily",  priority: 0.7 },
  ];
}
