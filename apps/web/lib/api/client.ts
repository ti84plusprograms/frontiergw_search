import type { components } from "@/lib/api/types";
import * as Sentry from "@sentry/nextjs";

export type AirportItem = components["schemas"]["AirportItem"];
export type AirportSearchResponse =
  components["schemas"]["AirportSearchResponse"];
export type SearchRequest = components["schemas"]["SearchRequest"];
export type SearchResponse = components["schemas"]["SearchResponse"];
export type ItineraryModel = components["schemas"]["ItineraryModel"];
export type ScheduleStatusResponse =
  components["schemas"]["ScheduleStatusResponse"];
export type ApiErrorResponse = components["schemas"]["ApiErrorResponse"];
export type ApiWarning = components["schemas"]["ApiWarning"];

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** A backend error carrying the stable public error code (distinguishes expected vs unexpected). */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly requestId: string | null;
  readonly details: unknown;
  readonly retryAfter: number | null;

  constructor(
    status: number,
    body: ApiErrorResponse | null,
    fallback: string,
    retryAfter?: string | null,
  ) {
    const err = body?.error;
    super(err?.message ?? fallback);
    this.name = "ApiError";
    this.code = err?.code ?? "INTERNAL_ERROR";
    this.status = status;
    this.requestId = err?.request_id ?? null;
    this.details = err?.details ?? null;
    const parsedRetry = retryAfter
      ? Number.parseInt(retryAfter, 10)
      : Number.NaN;
    this.retryAfter = Number.isFinite(parsedRetry) ? parsedRetry : null;
  }

  /** Expected (client-actionable) errors render differently from unexpected failures. */
  get isExpected(): boolean {
    return (
      (this.status >= 400 && this.status < 500) ||
      this.code === "NO_ACTIVE_SCHEDULE"
    );
  }
}

async function parseError(res: Response): Promise<ApiError> {
  let body: ApiErrorResponse | null = null;
  try {
    body = (await res.json()) as ApiErrorResponse;
  } catch {
    body = null;
  }
  const error = new ApiError(
    res.status,
    body,
    `Request failed with status ${res.status}`,
    res.headers.get("Retry-After"),
  );
  if (res.status >= 500) {
    Sentry.captureException(error, {
      tags: { request_id: error.requestId ?? "unknown" },
    });
  }
  return error;
}

export async function searchAirports(
  query: string,
  limit: number,
  signal?: AbortSignal,
): Promise<AirportSearchResponse> {
  const params = new URLSearchParams({ query, limit: String(limit) });
  const res = await fetch(
    `${API_BASE_URL}/api/v1/airports?${params.toString()}`,
    {
      signal,
      headers: { Accept: "application/json" },
    },
  );
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as AirportSearchResponse;
}

export async function postSearch(
  request: SearchRequest,
  signal?: AbortSignal,
): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(request),
    signal,
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as SearchResponse;
}

export async function getScheduleStatus(
  signal?: AbortSignal,
): Promise<ScheduleStatusResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/schedules/status`, {
    signal,
    headers: { Accept: "application/json" },
  });
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as ScheduleStatusResponse;
}
