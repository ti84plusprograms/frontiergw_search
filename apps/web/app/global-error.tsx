"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error, {
      tags: { event_id: error.digest ?? "unknown" },
    });
  }, [error]);

  return (
    <html lang="en">
      <body>
        <main className="mx-auto max-w-xl px-4 py-12">
          <h1 className="text-xl font-semibold">Something went wrong</h1>
          <p className="mt-2">
            The error was recorded without personal or search data.
          </p>
          {error.digest && (
            <p className="mt-2 text-sm">Reference: {error.digest}</p>
          )}
          <button
            className="mt-4 min-h-[44px] rounded border px-4"
            onClick={reset}
            type="button"
          >
            Try again
          </button>
        </main>
      </body>
    </html>
  );
}
