import type { SearchRequest } from "@/lib/api/client";

/** Supported sort modes (must mirror the backend SortMode enum exactly). */
export const SORT_MODES = [
  "PRICE",
  "TOTAL_DURATION",
  "EARLIEST_DEPARTURE",
  "LATEST_DEPARTURE",
  "DESTINATION",
] as const;
export type SortMode = (typeof SORT_MODES)[number];

/** The frontend's normalized search criteria (URL is the source of truth). */
export interface SearchCriteriaState {
  origin: string;
  date: string; // YYYY-MM-DD, used as the local calendar date (no tz shift)
  connections: 0 | 1;
  minConnMinutes?: number;
  maxConnMinutes?: number;
  departAfter?: string; // HH:MM
  departBefore?: string;
  arriveBefore?: string;
  maxDuration?: number;
  maxPrice?: number;
  domesticOnly?: boolean;
  internationalOnly?: boolean;
  sort: SortMode;
}

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const TIME_RE = /^([01]\d|2[0-3]):[0-5]\d$/;
const CODE_RE = /^[A-Za-z]{3}$/;

function toInt(value: string | null): number | undefined {
  if (value == null) return undefined;
  const n = Number(value);
  return Number.isFinite(n) && Number.isInteger(n) ? n : undefined;
}

function toNumber(value: string | null): number | undefined {
  if (value == null || value.trim() === "") return undefined;
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

function toTime(value: string | null): string | undefined {
  return value && TIME_RE.test(value) ? value : undefined;
}

function isCalendarDate(value: string): boolean {
  if (!DATE_RE.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

function optionalValue<T>(
  params: URLSearchParams,
  key: string,
  parse: (raw: string | null) => T | undefined,
  valid: (value: T) => boolean,
): { valid: boolean; value?: T } {
  const raw = params.get(key);
  if (raw == null) return { valid: true };
  const value = parse(raw);
  return value !== undefined && valid(value) ? { valid: true, value } : { valid: false };
}

/** Parse URL params into normalized criteria. Invalid values fall back safely. */
export function parseSearchParams(params: URLSearchParams): SearchCriteriaState | null {
  const originRaw = params.get("origin");
  const dateRaw = params.get("date");
  if (!originRaw || !CODE_RE.test(originRaw)) return null;
  if (!dateRaw || !isCalendarDate(dateRaw)) return null;

  const connectionsRaw = params.get("connections");
  if (connectionsRaw !== null && connectionsRaw !== "0" && connectionsRaw !== "1") return null;
  const connections: 0 | 1 = connectionsRaw === "1" ? 1 : 0;
  const sortRaw = params.get("sort");
  if (sortRaw !== null && !SORT_MODES.includes(sortRaw as SortMode)) return null;
  const sort: SortMode = (sortRaw as SortMode | null) ?? "PRICE";

  const domesticRaw = params.get("domestic");
  const internationalRaw = params.get("international");
  if (![null, "1"].includes(domesticRaw) || ![null, "1"].includes(internationalRaw)) return null;
  const domesticOnly = domesticRaw === "1";
  const internationalOnly = internationalRaw === "1";
  if (domesticOnly && internationalOnly) return null;

  const minConn = optionalValue(params, "min_conn", toInt, (value) => value >= 20 && value <= 360);
  const maxConn = optionalValue(params, "max_conn", toInt, (value) => value >= 20 && value <= 360);
  const maxDuration = optionalValue(
    params,
    "max_duration",
    toInt,
    (value) => value >= 60 && value <= 1440,
  );
  const maxPrice = optionalValue(params, "max_price", toNumber, (value) => value >= 0);
  const departAfter = optionalValue(params, "depart_after", toTime, () => true);
  const departBefore = optionalValue(params, "depart_before", toTime, () => true);
  const arriveBefore = optionalValue(params, "arrive_before", toTime, () => true);
  if (
    !minConn.valid ||
    !maxConn.valid ||
    !maxDuration.valid ||
    !maxPrice.valid ||
    !departAfter.valid ||
    !departBefore.valid ||
    !arriveBefore.valid
  ) {
    return null;
  }
  if ((maxConn.value ?? 240) <= (minConn.value ?? 45)) return null;

  return {
    origin: originRaw.toUpperCase(),
    date: dateRaw,
    connections,
    minConnMinutes: minConn.value,
    maxConnMinutes: maxConn.value,
    departAfter: departAfter.value,
    departBefore: departBefore.value,
    arriveBefore: arriveBefore.value,
    maxDuration: maxDuration.value,
    maxPrice: maxPrice.value,
    domesticOnly: domesticOnly || undefined,
    internationalOnly: internationalOnly || undefined,
    sort,
  };
}

/** Serialize criteria to a normalized URLSearchParams (defaults omitted). */
export function serializeSearchParams(state: SearchCriteriaState): URLSearchParams {
  const p = new URLSearchParams();
  p.set("origin", state.origin.toUpperCase());
  p.set("date", state.date);
  if (state.connections === 1) p.set("connections", "1");
  if (state.minConnMinutes != null && state.minConnMinutes !== 45)
    p.set("min_conn", String(state.minConnMinutes));
  if (state.maxConnMinutes != null && state.maxConnMinutes !== 240)
    p.set("max_conn", String(state.maxConnMinutes));
  if (state.departAfter) p.set("depart_after", state.departAfter);
  if (state.departBefore) p.set("depart_before", state.departBefore);
  if (state.arriveBefore) p.set("arrive_before", state.arriveBefore);
  if (state.maxDuration != null && state.maxDuration !== 720)
    p.set("max_duration", String(state.maxDuration));
  if (state.maxPrice != null) p.set("max_price", String(state.maxPrice));
  if (state.domesticOnly) p.set("domestic", "1");
  if (state.internationalOnly) p.set("international", "1");
  if (state.sort !== "PRICE") p.set("sort", state.sort);
  return p;
}

/** Map normalized criteria to the backend POST /search request body. */
export function toSearchRequest(state: SearchCriteriaState): SearchRequest {
  return {
    origin: state.origin.toUpperCase(),
    departure_date: state.date,
    max_connections: state.connections,
    min_connection_minutes: state.minConnMinutes ?? 45,
    max_connection_minutes: state.maxConnMinutes ?? 240,
    depart_after: state.departAfter ?? null,
    depart_before: state.departBefore ?? null,
    arrive_before: state.arriveBefore ?? null,
    max_total_duration_minutes: state.maxDuration ?? 720,
    max_price: state.maxPrice ?? null,
    domestic_only: state.domesticOnly ?? false,
    international_only: state.internationalOnly ?? false,
    sort: state.sort,
  };
}
