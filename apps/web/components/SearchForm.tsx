"use client";

import { AirportCombobox } from "@/components/AirportCombobox";
import { getScheduleStatus } from "@/lib/api/client";
import { SORT_MODES, serializeSearchParams, type SearchCriteriaState } from "@/lib/url/searchParams";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";

const SORT_LABELS: Record<string, string> = {
  PRICE: "Lowest estimated price",
  TOTAL_DURATION: "Shortest trip",
  EARLIEST_DEPARTURE: "Earliest departure",
  LATEST_DEPARTURE: "Latest departure",
  DESTINATION: "Destination",
};

interface Props {
  initial?: Partial<SearchCriteriaState>;
}

/** WEB-001 search form. Client validation aids usability; the backend re-validates. */
export function SearchForm({ initial }: Props) {
  const router = useRouter();
  const errId = useId();

  const [origin, setOrigin] = useState<string | null>(initial?.origin ?? null);
  const [date, setDate] = useState(initial?.date ?? "");
  const [connections, setConnections] = useState<0 | 1>(initial?.connections ?? 0);
  const [minConnMinutes, setMinConnMinutes] = useState(
    initial?.minConnMinutes?.toString() ?? "45",
  );
  const [maxConnMinutes, setMaxConnMinutes] = useState(
    initial?.maxConnMinutes?.toString() ?? "240",
  );
  const [departAfter, setDepartAfter] = useState(initial?.departAfter ?? "");
  const [departBefore, setDepartBefore] = useState(initial?.departBefore ?? "");
  const [arriveBefore, setArriveBefore] = useState(initial?.arriveBefore ?? "");
  const [maxDuration, setMaxDuration] = useState(initial?.maxDuration?.toString() ?? "720");
  const [maxPrice, setMaxPrice] = useState<string>(initial?.maxPrice?.toString() ?? "");
  const [domestic, setDomestic] = useState(initial?.domesticOnly ?? false);
  const [international, setInternational] = useState(initial?.internationalOnly ?? false);
  const [sort, setSort] = useState(initial?.sort ?? "PRICE");
  const [error, setError] = useState<string | null>(null);
  const [errorField, setErrorField] = useState<string | null>(null);
  const errorRef = useRef<HTMLParagraphElement>(null);

  const status = useQuery({ queryKey: ["schedule-status"], queryFn: () => getScheduleStatus() });
  const minDate = status.data?.effective_start ?? undefined;
  const maxDate = status.data?.effective_end ?? undefined;

  useEffect(() => {
    if (error) errorRef.current?.focus();
  }, [error]);

  function fail(message: string, field: string) {
    setErrorField(field);
    setError(message);
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!origin) return fail("Select a valid origin airport.", "origin");
    if (!date) return fail("Select a departure date.", "date");
    if ((minDate && date < minDate) || (maxDate && date > maxDate))
      return fail("Select a date within the supported schedule range.", "date");
    if (domestic && international)
      return fail("Choose domestic-only or international-only, not both.", "geography");
    const minConnection = Number(minConnMinutes);
    const maxConnection = Number(maxConnMinutes);
    const totalDuration = Number(maxDuration);
    const price = maxPrice === "" ? undefined : Number(maxPrice);
    if (!Number.isInteger(minConnection) || minConnection < 20 || minConnection > 360)
      return fail("Minimum connection must be between 20 and 360 minutes.", "min-connection");
    if (!Number.isInteger(maxConnection) || maxConnection < 20 || maxConnection > 360)
      return fail("Maximum connection must be between 20 and 360 minutes.", "max-connection");
    if (maxConnection <= minConnection)
      return fail(
        "Maximum connection must be greater than the minimum connection.",
        "max-connection",
      );
    if (!Number.isInteger(totalDuration) || totalDuration < 60 || totalDuration > 1440)
      return fail(
        "Maximum total duration must be between 60 and 1,440 minutes.",
        "max-duration",
      );
    if (price !== undefined && (!Number.isFinite(price) || price < 0))
      return fail("Maximum price cannot be negative.", "max-price");
    setError(null);
    setErrorField(null);

    const state: SearchCriteriaState = {
      origin,
      date,
      connections,
      minConnMinutes: minConnection,
      maxConnMinutes: maxConnection,
      departAfter: departAfter || undefined,
      departBefore: departBefore || undefined,
      arriveBefore: arriveBefore || undefined,
      maxDuration: totalDuration,
      maxPrice: price,
      domesticOnly: domestic || undefined,
      internationalOnly: international || undefined,
      sort,
    };
    router.push(`/results?${serializeSearchParams(state).toString()}`);
  }

  return (
    <form onSubmit={submit} noValidate>
      <h1 className="text-2xl font-bold">Where can you fly?</h1>
      <p className="mt-1 text-slate-600">
        Search Frontier GoWild destinations. Prices are estimates, not guaranteed fares.
      </p>

      {error && (
        <p
          id={errId}
          ref={errorRef}
          role="alert"
          tabIndex={-1}
          className="mt-3 rounded bg-red-50 px-3 py-2 text-red-800"
        >
          {error}
        </p>
      )}

      <div className="mt-4 space-y-4">
        <AirportCombobox
          value={origin}
          onSelect={(code) => setOrigin(code)}
          errorId={error && errorField === "origin" ? errId : undefined}
          invalid={!!error && errorField === "origin"}
        />

        {status.isError && (
          <p role="status" className="rounded bg-amber-50 px-3 py-2 text-sm text-amber-900">
            Could not load the supported schedule range. Your search will still be validated by
            the server.
          </p>
        )}

        <div>
          <label htmlFor="date" className="block text-sm font-medium">
            Departure date
          </label>
          <input
            id="date"
            type="date"
            className="mt-1 min-h-[44px] w-full rounded border border-slate-300 px-3 py-2"
            value={date}
            min={minDate}
            max={maxDate}
            aria-invalid={errorField === "date" || undefined}
            aria-describedby={errorField === "date" ? errId : undefined}
            onChange={(e) => setDate(e.target.value)}
          />
          {(minDate || maxDate) && (
            <p className="mt-1 text-xs text-slate-500">
              Supported range: {minDate ?? "—"} to {maxDate ?? "—"}
            </p>
          )}
        </div>

        <fieldset>
          <legend className="text-sm font-medium">Connections</legend>
          <div className="mt-1 flex gap-4">
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="connections"
                checked={connections === 0}
                onChange={() => setConnections(0)}
              />
              Direct only
            </label>
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="connections"
                checked={connections === 1}
                onChange={() => setConnections(1)}
              />
              Up to one stop
            </label>
          </div>
        </fieldset>

        <details className="rounded border border-slate-200 p-3">
          <summary className="cursor-pointer font-medium">Advanced filters</summary>
          <div className="mt-3 space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <NumberField
                id="min-connection"
                label="Minimum connection (minutes)"
                min={20}
                max={360}
                value={minConnMinutes}
                onChange={setMinConnMinutes}
                errorId={errorField === "min-connection" ? errId : undefined}
              />
              <NumberField
                id="max-connection"
                label="Maximum connection (minutes)"
                min={20}
                max={360}
                value={maxConnMinutes}
                onChange={setMaxConnMinutes}
                errorId={errorField === "max-connection" ? errId : undefined}
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <TimeField id="depart-after" label="Depart after" value={departAfter} onChange={setDepartAfter} />
              <TimeField id="depart-before" label="Depart before" value={departBefore} onChange={setDepartBefore} />
              <TimeField id="arrive-before" label="Arrive before" value={arriveBefore} onChange={setArriveBefore} />
            </div>
            <NumberField
              id="max-duration"
              label="Maximum total duration (minutes)"
              min={60}
              max={1440}
              value={maxDuration}
              onChange={setMaxDuration}
              errorId={errorField === "max-duration" ? errId : undefined}
            />
            <div>
              <label htmlFor="max-price" className="block text-sm font-medium">
                Maximum estimated price (USD)
              </label>
              <input
                id="max-price"
                type="number"
                min={0}
                step="0.01"
                aria-invalid={errorField === "max-price" || undefined}
                aria-describedby={errorField === "max-price" ? errId : undefined}
                className="mt-1 min-h-[44px] w-full rounded border border-slate-300 px-3 py-2"
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value)}
              />
            </div>
            <fieldset
              className="flex flex-col gap-2"
              aria-invalid={errorField === "geography" || undefined}
              aria-describedby={errorField === "geography" ? errId : undefined}
            >
              <legend className="text-sm font-medium">Destination type</legend>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={domestic} onChange={(e) => setDomestic(e.target.checked)} />
                Domestic only
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={international}
                  onChange={(e) => setInternational(e.target.checked)}
                />
                International only
              </label>
            </fieldset>
          </div>
        </details>

        <div>
          <label htmlFor="sort" className="block text-sm font-medium">
            Sort by
          </label>
          <select
            id="sort"
            className="mt-1 min-h-[44px] w-full rounded border border-slate-300 px-3 py-2"
            value={sort}
            onChange={(e) => setSort(e.target.value as (typeof SORT_MODES)[number])}
          >
            {SORT_MODES.map((mode) => (
              <option key={mode} value={mode}>
                {SORT_LABELS[mode]}
              </option>
            ))}
          </select>
        </div>

        <button
          type="submit"
          disabled={!origin || !date}
          className="min-h-[44px] w-full rounded bg-blue-700 px-4 py-2 font-medium text-white disabled:opacity-50"
        >
          Search destinations
        </button>
      </div>
    </form>
  );
}

function NumberField({
  id,
  label,
  min,
  max,
  value,
  onChange,
  errorId,
}: {
  id: string;
  label: string;
  min: number;
  max: number;
  value: string;
  onChange: (value: string) => void;
  errorId?: string;
}) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        type="number"
        min={min}
        max={max}
        step={1}
        aria-invalid={!!errorId || undefined}
        aria-describedby={errorId}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 min-h-[44px] w-full rounded border border-slate-300 px-3 py-2"
      />
    </div>
  );
}

function TimeField({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        type="time"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 min-h-[44px] w-full rounded border border-slate-300 px-3 py-2"
      />
    </div>
  );
}
