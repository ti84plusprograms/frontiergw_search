"use client";

import { ItineraryCard } from "@/components/ItineraryCard";
import { ApiError, postSearch } from "@/lib/api/client";
import {
  SORT_MODES,
  parseSearchParams,
  serializeSearchParams,
  toSearchRequest,
  type SortMode,
} from "@/lib/url/searchParams";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

const SORT_LABELS: Record<SortMode, string> = {
  PRICE: "Lowest estimated price",
  TOTAL_DURATION: "Shortest trip",
  EARLIEST_DEPARTURE: "Earliest departure",
  LATEST_DEPARTURE: "Latest departure",
  DESTINATION: "Destination",
};

export function ResultsView() {
  const router = useRouter();
  const params = useSearchParams();
  const criteria = parseSearchParams(new URLSearchParams(params.toString()));

  const query = useQuery({
    queryKey: ["search", criteria && serializeSearchParams(criteria).toString()],
    queryFn: ({ signal }) => postSearch(toSearchRequest(criteria!), signal),
    enabled: !!criteria,
    retry: (count, err) => !(err instanceof ApiError && err.isExpected) && count < 1,
  });

  if (!criteria) {
    return (
      <section>
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-red-800">
          This search link is missing or has invalid parameters.
        </p>
        <Link href="/" className="mt-3 inline-block text-blue-700 underline">
          Start a new search
        </Link>
      </section>
    );
  }

  function changeSort(sort: SortMode) {
    router.push(`/results?${serializeSearchParams({ ...criteria!, sort }).toString()}`);
  }

  return (
    <section aria-labelledby="results-heading">
      <h1 id="results-heading" className="text-2xl font-bold">
        Destinations from {criteria.origin}
      </h1>

      <p className="mt-1 text-slate-600">
        {criteria.date} · {criteria.connections === 1 ? "Up to one stop" : "Direct only"}
        {criteria.domesticOnly && " · Domestic"}
        {criteria.internationalOnly && " · International"}
        {criteria.maxPrice != null && ` · ≤ $${criteria.maxPrice}`}
        {` · ${SORT_LABELS[criteria.sort]}`}
      </p>

      <Link
        href={`/?${serializeSearchParams(criteria).toString()}`}
        className="mt-2 inline-block text-sm text-blue-700 underline"
      >
        Modify this search
      </Link>

      <div className="mt-4 flex items-center gap-2">
        <label htmlFor="sort" className="text-sm font-medium">
          Sort by
        </label>
        <select
          id="sort"
          className="min-h-[44px] rounded border border-slate-300 px-2 py-1"
          value={criteria.sort}
          onChange={(e) => changeSort(e.target.value as SortMode)}
        >
          {SORT_MODES.map((mode) => (
            <option key={mode} value={mode}>
              {SORT_LABELS[mode]}
            </option>
          ))}
        </select>
      </div>

      <div aria-live="polite" className="mt-4">
        {query.isLoading && (
          <div role="status" className="space-y-3">
            <p className="text-slate-600">Searching…</p>
            <div className="h-24 animate-pulse rounded bg-slate-100" />
            <div className="h-24 animate-pulse rounded bg-slate-100" />
          </div>
        )}

        {query.isError && <ErrorState error={query.error} onRetry={() => query.refetch()} />}

        {query.data && (
          <>
            <FreshnessPanel data={query.data} />
            <Warnings warnings={query.data.warnings} />
            <p className="mt-2 font-medium">{query.data.result_count} result(s)</p>
            {query.data.results.length === 0 ? (
              <p className="mt-4 rounded bg-slate-50 px-3 py-6 text-center text-slate-600">
                No Frontier destinations matched your criteria. Try enabling one stop or
                widening filters.
              </p>
            ) : (
              <ul className="mt-4 space-y-4">
                {query.data.results.map((it) => (
                  <ItineraryCard key={it.itinerary_id} itinerary={it} />
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </section>
  );
}

function ErrorState({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const expected = error instanceof ApiError && error.isExpected;
  const noSchedule = error instanceof ApiError && error.code === "NO_ACTIVE_SCHEDULE";
  const requestId = error instanceof ApiError ? error.requestId : null;
  return (
    <div role="alert" className="rounded bg-red-50 px-3 py-3 text-red-800">
      <p className="font-medium">
        {noSchedule
          ? "Schedule data is temporarily unavailable"
          : expected
            ? "We couldn't run that search"
            : "Something went wrong"}
      </p>
      <p className="text-sm">
        {error instanceof ApiError ? error.message : "A network or server error occurred."}
      </p>
      {!expected && requestId && (
        <p className="mt-1 text-xs text-red-600">Reference: {requestId}</p>
      )}
      <button
        type="button"
        onClick={onRetry}
        className="mt-2 min-h-[44px] rounded border border-red-700 px-3 py-1 font-medium"
      >
        Retry
      </button>
    </div>
  );
}

function FreshnessPanel({ data }: { data: import("@/lib/api/client").SearchResponse }) {
  const f = data.data_freshness;
  return (
    <details className="rounded border border-slate-200 p-3 text-sm text-slate-600">
      <summary className="cursor-pointer font-medium text-slate-800">Data freshness</summary>
      <ul className="mt-2 space-y-1">
        <li>Schedule source: {f.schedule_source ?? "—"}</li>
        <li>Schedule version: {f.schedule_version ?? "—"}</li>
        <li>Updated: {f.schedule_updated_at ?? "—"}</li>
        <li>
          Supported range: {f.schedule_effective_start ?? "—"} to{" "}
          {f.schedule_effective_end ?? "—"}
        </li>
        <li className="font-medium text-amber-800">
          Live GoWild availability has not been checked.
        </li>
      </ul>
    </details>
  );
}

function Warnings({ warnings }: { warnings: import("@/lib/api/client").ApiWarning[] }) {
  if (warnings.length === 0) return null;
  return (
    <ul className="mt-3 space-y-1">
      {warnings.map((w) => (
        <li key={w.code} className="rounded bg-amber-50 px-3 py-1 text-sm text-amber-900">
          {w.message}
        </li>
      ))}
    </ul>
  );
}
