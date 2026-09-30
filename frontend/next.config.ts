import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // The repo root also has its own package-lock.json (for `concurrently`,
  // which runs poller/backend/frontend together) — without this, Next.js
  // can't tell which lockfile marks the real workspace root and warns on
  // every build.
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
