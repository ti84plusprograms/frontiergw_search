import { ResultsView } from "@/components/ResultsView";
import { Suspense } from "react";

export default function ResultsPage() {
  return (
    <Suspense fallback={<p role="status">Loading search…</p>}>
      <ResultsView />
    </Suspense>
  );
}
