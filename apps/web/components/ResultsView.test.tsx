import { ResultsView } from "@/components/ResultsView";
import { ApiError, postSearch } from "@/lib/api/client";
import { itinerary, searchResponse } from "@/test/fixtures";
import { renderWithQueryClient } from "@/test/render";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { beforeEach, describe, expect, it, vi } from "vitest";

let params = "origin=ATL&date=2026-08-04";
const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  useSearchParams: () => new URLSearchParams(params),
}));
vi.mock("@/lib/api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/api/client")>();
  return { ...original, postSearch: vi.fn() };
});

describe("ResultsView", () => {
  beforeEach(() => {
    params = "origin=ATL&date=2026-08-04";
    push.mockReset();
    vi.mocked(postSearch).mockReset();
  });

  it("renders results, freshness, empty state, and honest warnings", async () => {
    const response = searchResponse();
    response.warnings.push({
      code: "RESULTS_TRUNCATED",
      message: "Results were limited to 250 itineraries.",
    });
    vi.mocked(postSearch).mockResolvedValue(response);
    const { container } = renderWithQueryClient(<ResultsView />);
    expect(await screen.findByRole("heading", { name: "Denver (DEN)" })).toBeInTheDocument();
    expect(screen.getByText("1 result(s)")).toBeInTheDocument();
    expect(screen.getByText("Data freshness")).toBeInTheDocument();
    expect(screen.getByText("GoWild availability has not been verified.")).toBeInTheDocument();
    expect(screen.getByText("Results were limited to 250 itineraries.")).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it("does not present prior-query data under changed criteria", async () => {
    vi.mocked(postSearch).mockResolvedValueOnce(searchResponse());
    const view = renderWithQueryClient(<ResultsView />);
    expect(await screen.findByRole("heading", { name: "Denver (DEN)" })).toBeInTheDocument();

    let resolve!: (value: ReturnType<typeof searchResponse>) => void;
    vi.mocked(postSearch).mockReturnValueOnce(new Promise((done) => (resolve = done)));
    params = "origin=ATL&date=2026-08-04&sort=DESTINATION";
    view.rerender(<ResultsView />);
    expect(screen.queryByRole("heading", { name: "Denver (DEN)" })).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Searching");
    resolve(searchResponse([itinerary({ destination: { code: "LAS", city: "Las Vegas", country_code: "US" } })]));
    expect(await screen.findByRole("heading", { name: "Las Vegas (LAS)" })).toBeInTheDocument();
  });

  it("renders no results and rejects invalid shared links", async () => {
    vi.mocked(postSearch).mockResolvedValue(searchResponse([]));
    const view = renderWithQueryClient(<ResultsView />);
    expect(await screen.findByText(/No Frontier destinations matched/)).toBeInTheDocument();

    params = "origin=ATL&date=2026-02-30";
    view.rerender(<ResultsView />);
    expect(screen.getByRole("alert")).toHaveTextContent("invalid parameters");
    expect(screen.getByRole("link", { name: "Start a new search" })).toHaveAttribute("href", "/");
  });

  it("presents no active schedule as an expected service state", async () => {
    vi.mocked(postSearch).mockRejectedValue(
      new ApiError(
        503,
        {
          error: {
            code: "NO_ACTIVE_SCHEDULE",
            message: "No active schedule dataset is available.",
            details: null,
            request_id: "req-test",
          },
        },
        "failed",
      ),
    );
    renderWithQueryClient(<ResultsView />);
    expect(await screen.findByText("Schedule data is temporarily unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Something went wrong")).not.toBeInTheDocument();
    expect(postSearch).toHaveBeenCalledOnce();
  });

  it("updates sort in URL state", async () => {
    vi.mocked(postSearch).mockResolvedValue(searchResponse());
    renderWithQueryClient(<ResultsView />);
    await screen.findByRole("heading", { name: "Denver (DEN)" });
    await userEvent.selectOptions(screen.getByLabelText("Sort by"), "DESTINATION");
    await waitFor(() => expect(push).toHaveBeenCalledWith(expect.stringContaining("sort=DESTINATION")));
  });
});
