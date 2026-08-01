"use client";

import type { ItineraryModel } from "@/lib/api/client";
import {
  crossesMidnight,
  formatDuration,
  formatMoney,
  localDate,
  localTime,
  offsetLabel,
} from "@/lib/format/display";

/** WEB-003 itinerary card. Honest pricing/availability language; never implies bookable. */
export function ItineraryCard({ itinerary }: { itinerary: ItineraryModel }) {
  const direct = itinerary.connection_count === 0;
  const dateChange = crossesMidnight(itinerary.departure_at, itinerary.arrival_at);
  const priceLabel =
    itinerary.price.status === "ESTIMATED"
      ? "Estimated"
      : itinerary.price.status === "VERIFIED"
        ? "Verified"
        : null;

  return (
    <li className="rounded-lg border border-slate-200 p-4 shadow-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold">
          {itinerary.destination.city || itinerary.destination.code}{" "}
          <span className="text-slate-500">({itinerary.destination.code})</span>
        </h2>
        {direct ? (
          <span className="rounded bg-green-100 px-2 py-0.5 text-sm font-medium text-green-900">
            ● Direct
          </span>
        ) : (
          <span className="rounded bg-amber-100 px-2 py-0.5 text-sm font-medium text-amber-900">
            ● 1 stop
          </span>
        )}
      </div>

      <p className="mt-1 text-slate-700">
        <time dateTime={itinerary.departure_at}>{localTime(itinerary.departure_at)}</time> →{" "}
        <time dateTime={itinerary.arrival_at}>{localTime(itinerary.arrival_at)}</time>
        {dateChange && (
          <span className="ml-1 text-amber-700"> (arrives {localDate(itinerary.arrival_at)})</span>
        )}
        <span className="ml-2 text-sm text-slate-500">
          {offsetLabel(itinerary.departure_at)} → {offsetLabel(itinerary.arrival_at)}
        </span>
      </p>

      <p className="text-sm text-slate-600">
        Total {formatDuration(itinerary.total_duration_minutes)} · Airborne{" "}
        {formatDuration(itinerary.airborne_duration_minutes)}
        {!direct && <> · Layover {formatDuration(itinerary.total_layover_minutes)}</>}
      </p>

      <ol className="mt-3 space-y-1 border-l-2 border-slate-200 pl-3 text-sm">
        {itinerary.segments.map((seg, i) => (
          <li key={seg.sequence}>
            <span className="font-medium">
              {seg.origin} → {seg.destination}
            </span>{" "}
            · {seg.carrier} {seg.flight_number} ·{" "}
            <time dateTime={seg.departure_at}>{localTime(seg.departure_at)}</time>–
            <time dateTime={seg.arrival_at}>{localTime(seg.arrival_at)}</time>
            {i < itinerary.segments.length - 1 && (
              <span className="text-slate-500"> · connect at {seg.destination}</span>
            )}
          </li>
        ))}
      </ol>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-lg font-semibold">
            {priceLabel && itinerary.price.amount !== null
              ? `${priceLabel}: ${formatMoney(itinerary.price.amount, itinerary.price.currency)}`
              : "Price unavailable"}
            <span className="ml-2 align-middle text-xs font-normal uppercase tracking-wide text-slate-500">
              {itinerary.price.status}
            </span>
          </p>
          {/* Not color-only: explicit text for availability (WCAG 1.4.1). */}
          <p className="text-sm text-slate-600">Availability not checked</p>
        </div>
        <a
          href="https://www.flyfrontier.com/deals/gowild/"
          target="_blank"
          rel="noopener noreferrer"
          className="min-h-[44px] rounded border border-blue-700 px-4 py-2 font-medium text-blue-700"
        >
          Check on Frontier
        </a>
      </div>

      <p className="mt-2 text-xs text-slate-500">{itinerary.price.disclaimer}</p>
    </li>
  );
}
