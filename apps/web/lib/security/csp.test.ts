import { describe, expect, it } from "vitest";
import { buildContentSecurityPolicy } from "./csp";

describe("buildContentSecurityPolicy", () => {
  it("allows the configured preview API origin without broad wildcards", () => {
    const policy = buildContentSecurityPolicy(
      "https://api.preview.example:8443/api/v1",
    );
    expect(policy).toContain(
      "connect-src 'self' https://api.preview.example:8443",
    );
    expect(policy).not.toContain("api.preview.example:8443/api/v1");
    expect(policy).toContain("frame-ancestors 'none'");
    expect(policy).not.toContain("'unsafe-eval'");
  });

  it("permits eval only when explicitly building the development policy", () => {
    const policy = buildContentSecurityPolicy("http://localhost:8000", true);
    expect(policy).toContain("script-src 'self' 'unsafe-inline' 'unsafe-eval'");
  });
});
