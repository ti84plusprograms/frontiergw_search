export function buildContentSecurityPolicy(
  apiBaseUrl: string,
  allowDevelopmentEval = false,
): string {
  const apiOrigin = new URL(apiBaseUrl).origin;
  const scriptSource = allowDevelopmentEval
    ? "script-src 'self' 'unsafe-inline' 'unsafe-eval'"
    : "script-src 'self' 'unsafe-inline'";
  return [
    "default-src 'self'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
    "form-action 'self'",
    "img-src 'self' data:",
    "style-src 'self' 'unsafe-inline'",
    scriptSource,
    `connect-src 'self' ${apiOrigin} https://*.sentry.io`,
    "object-src 'none'",
  ].join("; ");
}
