import { AirportCombobox } from "@/components/AirportCombobox";
import { searchAirports } from "@/lib/api/client";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/hooks/useDebouncedValue", () => ({ useDebouncedValue: (value: string) => value }));
vi.mock("@/lib/api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/api/client")>();
  return { ...original, searchAirports: vi.fn() };
});

const ATL = {
  code: "ATL",
  name: "Synthetic Atlanta Airport",
  city: "Atlanta",
  state_or_region: "Georgia",
  country_code: "US",
  timezone: "America/New_York",
};

describe("AirportCombobox", () => {
  beforeEach(() => vi.mocked(searchAirports).mockReset());

  it("restores a selected airport value", () => {
    render(<AirportCombobox value="ATL" onSelect={vi.fn()} />);
    expect(screen.getByRole("combobox")).toHaveValue("ATL");
  });

  it("announces loading and selects a result with the keyboard", async () => {
    let resolve!: (value: { items: typeof ATL[]; count: number }) => void;
    vi.mocked(searchAirports).mockReturnValue(new Promise((done) => (resolve = done)));
    const onSelect = vi.fn();
    render(<AirportCombobox value={null} onSelect={onSelect} />);

    const combobox = screen.getByRole("combobox");
    combobox.focus();
    fireEvent.change(combobox, { target: { value: "atl" } });
    expect(await screen.findByText("Searching airports")).toBeInTheDocument();
    await act(async () => resolve({ items: [ATL], count: 1 }));
    await screen.findByRole("option", { name: /ATL.*Atlanta/ });
    await userEvent.keyboard("{Enter}");
    expect(onSelect).toHaveBeenLastCalledWith("ATL", ATL);
    expect(screen.getByRole("combobox")).toHaveValue("ATL — Atlanta");
  });

  it("selects a result with a pointer", async () => {
    vi.mocked(searchAirports).mockResolvedValue({ items: [ATL], count: 1 });
    const onSelect = vi.fn();
    render(<AirportCombobox value={null} onSelect={onSelect} />);

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "atl" } });
    await userEvent.click(await screen.findByRole("option", { name: /ATL.*Atlanta/ }));
    expect(onSelect).toHaveBeenLastCalledWith("ATL", ATL);
  });

  it("renders no-match and request-error states", async () => {
    vi.mocked(searchAirports).mockResolvedValueOnce({ items: [], count: 0 });
    const { rerender } = render(<AirportCombobox value={null} onSelect={vi.fn()} />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "zzz" } });
    await waitFor(() => expect(screen.getAllByText("No matching airports").length).toBeGreaterThan(0));

    vi.mocked(searchAirports).mockRejectedValueOnce(new Error("network"));
    rerender(<AirportCombobox value={null} onSelect={vi.fn()} />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "atl" } });
    expect(await screen.findByText("Could not load airports. Try again.")).toBeInTheDocument();
  });

  it("has no automated accessibility violations", async () => {
    const { container } = render(<AirportCombobox value={null} onSelect={vi.fn()} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
