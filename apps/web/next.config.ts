import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";
import { buildContentSecurityPolicy } from "./lib/security/csp";

const csp = buildContentSecurityPolicy(
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
  process.env.NODE_ENV !== "production",
);

const config: NextConfig = {
  reactStrictMode: true,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: csp },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), geolocation=(), microphone=(), payment=()",
          },
        ],
      },
    ];
  },
};

export default withSentryConfig(config, {
  silent: true,
  sourcemaps: { disable: false },
});
