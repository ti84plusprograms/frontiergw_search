import { SearchForm } from "@/components/SearchForm";
import { getScheduleStatus } from "@/lib/api/client";
import { renderWithQueryClient } from "@/test/render";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/api/client")>();
  return { ...original, getScheduleStatus: vi.fn() };
});

const STATUS = {
  active: true,
  source: "synthetic",
  version: "v1",
  retrieved_at: "2026-08-01T12:00:00+00:00",
  effective_start: "2026-08-01",
  effective_end: "2026-10-31",
  route_count: 1,
  scheduled_flight_count: 1,
};

describe("SearchForm", () => {
  beforeEach(() => {
    push.mockReset();
    vi.mocked(getScheduleStatus).mockResolvedValue(STATUS);
  });

  it("requires an airport and departure date before submission", () => {
    renderWithQueryClient(<SearchForm />);
    expect(screen.getByRole("button", { name: "Search destinations" })).toBeDisabled();
    expect(push).not.toHaveBeenCalled();
  });

  it("restores state and exposes every supported advanced filter", async () => {
    renderWithQueryClient(
      <SearchForm initial={{ origin: "ATL", date: "2026-08-04", connections: 1, sort: "PRICE" }} />,
    );
    expect(screen.getByRole("combobox", { name: "Origin airport" })).toHaveValue("ATL");
    await userEvent.click(screen.getByText("Advanced filters"));
    for (const label of [
      "Minimum connection (minutes)",
      "Maximum connection (minutes)",
      "Depart after",
      "Depart before",
      "Arrive before",
      "Maximum total duration (minutes)",
      "Maximum estimated price (USD)",
    ]) {
      expect(screen.getByLabelText(label)).toBeInTheDocument();
    }
  });

  it("submits a normalized URL containing decimal and advanced criteria", async () => {
    renderWithQueryClient(
      <SearchForm initial={{ origin: "ATL", date: "2026-08-04", connections: 1, sort: "PRICE" }} />,
    );
    await userEvent.click(screen.getByText("Advanced filters"));
    fireEvent.change(screen.getByLabelText("Minimum connection (minutes)"), { target: { value: "60" } });
    fireEvent.change(screen.getByLabelText("Maximum connection (minutes)"), { target: { value: "300" } });
    fireEvent.change(screen.getByLabelText("Depart after"), { target: { value: "06:00" } });
    fireEvent.change(screen.getByLabelText("Maximum total duration (minutes)"), { target: { value: "900" } });
    fireEvent.change(screen.getByLabelText("Maximum estimated price (USD)"), { target: { value: "12.50" } });
    await userEvent.click(screen.getByRole("button", { name: "Search destinations" }));
    expect(push).toHaveBeenCalledOnce();
    const target = push.mock.calls[0][0] as string;
    expect(target).toContain("/results?");
    expect(target).toContain("min_conn=60");
    expect(target).toContain("max_conn=300");
    expect(target).toContain("max_duration=900");
    expect(target).toContain("max_price=12.5");
  });

  it("rejects schedule-range and connection-range errors and focuses the alert", async () => {
    renderWithQueryClient(
      <SearchForm initial={{ origin: "ATL", date: "2027-01-01", connections: 1, sort: "PRICE" }} />,
    );
    await waitFor(() => expect(getScheduleStatus).toHaveBeenCalled());
    await userEvent.click(screen.getByRole("button", { name: "Search destinations" }));
    const dateAlert = await screen.findByRole("alert");
    expect(dateAlert).toHaveTextContent("supported schedule range");
    expect(dateAlert).toHaveFocus();
    expect(screen.getByLabelText("Departure date")).toHaveAttribute(
      "aria-describedby",
      dateAlert.id,
    );

    fireEvent.change(screen.getByLabelText("Departure date"), { target: { value: "2026-08-04" } });
    await userEvent.click(screen.getByText("Advanced filters"));
    fireEvent.change(screen.getByLabelText("Minimum connection (minutes)"), { target: { value: "300" } });
    fireEvent.change(screen.getByLabelText("Maximum connection (minutes)"), { target: { value: "60" } });
    await userEvent.click(screen.getByRole("button", { name: "Search destinations" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("greater than the minimum");
    expect(push).not.toHaveBeenCalled();
  });

  it("rejects contradictory geography filters", async () => {
    renderWithQueryClient(
      <SearchForm
        initial={{
          origin: "ATL",
          date: "2026-08-04",
          domesticOnly: true,
          internationalOnly: true,
        }}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Search destinations" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "domestic-only or international-only",
    );
    expect(screen.getByRole("group", { name: "Destination type" })).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(push).not.toHaveBeenCalled();
  });

  it("shows a bounded warning when schedule status cannot load", async () => {
    vi.mocked(getScheduleStatus).mockRejectedValue(new Error("offline"));
    renderWithQueryClient(<SearchForm />);
    expect(await screen.findByText(/Could not load the supported schedule range/)).toBeInTheDocument();
  });

  it("has no automated accessibility violations", async () => {
    const { container } = renderWithQueryClient(<SearchForm />);
    await screen.findByText(/Supported range:/);
    expect(await axe(container)).toHaveNoViolations();
  });
});
