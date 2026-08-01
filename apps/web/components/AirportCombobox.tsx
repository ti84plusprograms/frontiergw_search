"use client";

import { searchAirports, type AirportItem, ApiError } from "@/lib/api/client";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { useEffect, useId, useRef, useState } from "react";

interface Props {
  value: string | null; // selected airport code
  onSelect: (code: string | null, airport: AirportItem | null) => void;
  label?: string;
  errorId?: string;
  invalid?: boolean;
}

type Status = "idle" | "loading" | "loaded" | "error";

/**
 * Accessible airport combobox (WAI-ARIA 1.2 combobox pattern). Keyboard: ArrowUp/Down,
 * Home/End, Enter to select, Escape to close. Debounced queries with stale-request
 * cancellation. Stores the selected airport CODE, never free text.
 */
export function AirportCombobox({ value, onSelect, label = "Origin airport", errorId, invalid }: Props) {
  const [input, setInput] = useState("");
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<AirportItem[]>([]);
  const [active, setActive] = useState(-1);
  const [status, setStatus] = useState<Status>("idle");

  const debounced = useDebouncedValue(input, 250);
  const listId = useId();
  const inputId = useId();
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (value === null) {
      setInput("");
      return;
    }
    setInput((current) => (current.startsWith(`${value} —`) ? current : value));
  }, [value]);

  useEffect(() => {
    const q = debounced.trim();
    if (value && (q === value || q.startsWith(`${value} —`))) {
      setItems([]);
      setStatus("idle");
      return;
    }
    if (q.length < 1) {
      setItems([]);
      setStatus("idle");
      return;
    }
    const controller = new AbortController();
    setStatus("loading");
    searchAirports(q, 10, controller.signal)
      .then((res) => {
        setItems(res.items);
        setActive(res.items.length ? 0 : -1);
        setStatus("loaded");
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        if (err instanceof ApiError && err.status === 422) {
          setItems([]);
          setStatus("loaded");
          return;
        }
        setStatus("error");
      });
    return () => controller.abort(); // cancel stale requests
  }, [debounced, value]);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  function select(item: AirportItem) {
    onSelect(item.code, item);
    setInput(`${item.code} — ${item.city}`);
    setOpen(false);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActive((i) => Math.min(i + 1, items.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === "Home" && open) {
      e.preventDefault();
      setActive(0);
    } else if (e.key === "End" && open) {
      e.preventDefault();
      setActive(items.length - 1);
    } else if (e.key === "Enter") {
      if (open && active >= 0 && items[active]) {
        e.preventDefault();
        select(items[active]);
      }
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  const activeId = active >= 0 && items[active] ? `${listId}-opt-${active}` : undefined;

  return (
    <div ref={rootRef} className="relative">
      <label htmlFor={inputId} className="block text-sm font-medium">
        {label}
      </label>
      <input
        id={inputId}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={activeId}
        aria-invalid={invalid || undefined}
        aria-describedby={errorId}
        autoComplete="off"
        className="mt-1 min-h-[44px] w-full rounded border border-slate-300 px-3 py-2"
        value={input}
        placeholder="Code or city (e.g. ATL)"
        onChange={(e) => {
          setInput(e.target.value);
          setOpen(true);
          onSelect(null, null); // typing invalidates a prior selection
        }}
        onFocus={() => input.trim() && setOpen(true)}
        onKeyDown={onKeyDown}
      />

      {/* Screen-reader status for async states. */}
      <span role="status" aria-live="polite" className="sr-only">
        {status === "loading" ? "Searching airports" : ""}
        {status === "loaded" && items.length === 0 ? "No matching airports" : ""}
        {status === "error" ? "Error searching airports" : ""}
      </span>

      {open && (
        <ul
          id={listId}
          role="listbox"
          aria-label="Airport results"
          className="absolute z-10 mt-1 max-h-64 w-full overflow-auto rounded border border-slate-300 bg-white shadow"
        >
          {status === "loading" && (
            <li className="px-3 py-2 text-slate-500">Searching…</li>
          )}
          {status === "error" && (
            <li className="px-3 py-2 text-red-700">Could not load airports. Try again.</li>
          )}
          {status === "loaded" && items.length === 0 && (
            <li className="px-3 py-2 text-slate-500">No matching airports</li>
          )}
          {items.map((item, i) => (
            <li
              key={item.code}
              id={`${listId}-opt-${i}`}
              role="option"
              aria-selected={i === active}
              className={`min-h-[44px] cursor-pointer px-3 py-2 ${
                i === active ? "bg-blue-700 text-white" : ""
              }`}
              onMouseEnter={() => setActive(i)}
              onMouseDown={(e) => {
                e.preventDefault();
              }}
              onClick={() => select(item)}
            >
              <span className="font-medium">{item.code}</span> — {item.city}
              {item.state_or_region ? `, ${item.state_or_region}` : ""}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
