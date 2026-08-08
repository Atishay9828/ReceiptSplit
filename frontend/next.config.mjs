const sensitiveRouteHeaders = [
  { key: "X-Robots-Tag", value: "noindex, nofollow" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'" }
];

const nextConfig = {
  reactStrictMode: true,
  turbopack: {
    resolveAlias: {
      "@techstark/opencv-js": "./lib/ocr/opencv-shim.ts",
      "ort.bundle.min.mjs": "./lib/ocr/ort-bundle-shim.mjs"
    }
  },
  async headers() {
    return [
      { source: "/join/:inviteToken", headers: sensitiveRouteHeaders },
      { source: "/dashboard", headers: sensitiveRouteHeaders },
      { source: "/rooms/:roomId", headers: sensitiveRouteHeaders },
      { source: "/rooms/:roomId/creator", headers: sensitiveRouteHeaders }
    ];
  }
};

export default nextConfig;
