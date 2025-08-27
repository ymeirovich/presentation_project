import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: false, // Disable strict mode to prevent double hydration warnings
  experimental: {
    optimizePackageImports: ['lucide-react', '@radix-ui/react-tooltip'], // Optimize common packages
  },
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error']
    } : false,
  }
};

export default nextConfig;
