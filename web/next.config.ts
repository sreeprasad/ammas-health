import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  serverExternalPackages: ["mongodb", "mongodb-client-encryption"],
};

export default nextConfig;
