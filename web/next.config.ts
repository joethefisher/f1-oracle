import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  basePath: "/f1-oracle",
  // basePath means the app serves at joeking.ai/f1-oracle. But Google crawlers
  // look for /robots.txt and /sitemap.xml at the DOMAIN root, not the basePath.
  // Rewrites here let joeking.ai/robots.txt and joeking.ai/sitemap.xml resolve
  // into the basePath'd metadata routes.
  async rewrites() {
    return {
      beforeFiles: [
        { source: "/robots.txt", destination: "/f1-oracle/robots.txt" },
        { source: "/sitemap.xml", destination: "/f1-oracle/sitemap.xml" },
      ],
      afterFiles: [],
      fallback: [],
    };
  },
};

export default nextConfig;
