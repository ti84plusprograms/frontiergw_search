/**
 * Display formatters. Times are rendered from the server-provided ISO strings WITH
 * their offsets — the frontend never recomputes durations or shifts timezones
 * (backend is authoritative). We read the wall-clock/offset directly off the string.
 */

/** Extract "HH:MM" local wall-clock time from an ISO-8601 string with offset. */
export function localTime(iso: string): string {
  const m = iso.match(/T(\d{2}:\d{2})/);
  return m ? m[1] : iso;
}

/** Extract "YYYY-MM-DD" local date from an ISO-8601 string. */
export function localDate(iso: string): string {
  const m = iso.match(/^(\d{4}-\d{2}-\d{2})/);
  return m ? m[1] : iso;
}

/** Extract the UTC offset (e.g. "-04:00" or "Z") for timezone context display. */
export function offsetLabel(iso: string): string {
  const m = iso.match(/(Z|[+-]\d{2}:\d{2})$/);
  return m ? (m[1] === "Z" ? "UTC" : `UTC${m[1]}`) : "";
}

/** Human duration from whole minutes, e.g. 210 -> "3h 30m". */
export function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

/** Format the money string from the API (already decimal-safe) for display. */
export function formatMoney(amount: string | null, currency: string): string {
  if (amount == null) return "Unavailable";
  const symbol = currency === "USD" ? "$" : "";
  return `${symbol}${amount}`;
}

/** True when arrival calendar date differs from departure (cross-midnight). */
export function crossesMidnight(departIso: string, arriveIso: string): boolean {
  return localDate(departIso) !== localDate(arriveIso);
}
