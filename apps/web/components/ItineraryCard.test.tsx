import { ItineraryCard } from "@/components/ItineraryCard";
import { itinerary } from "@/test/fixtures";
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it } from "vitest";

describe("ItineraryCard", () => {
  it("labels an estimate and availability honestly", () => {
    render(<ul><ItineraryCard itinerary={itinerary()} /></ul>);
    expect(screen.getByText(/Direct/)).toBeInTheDocument();
    expect(screen.getByText(/Estimated: \$14\.91/)).toBeInTheDocument();
    expect(screen.getByText("Availability not checked")).toBeInTheDocument();
    expect(screen.getByText(/Final taxes, fees/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Check on Frontier" })).toHaveAttribute(
      "href",
      "https://www.flyfrontier.com/deals/gowild/",
    );
  });

  it("does not call an unavailable price estimated", () => {
    render(
      <ul>
        <ItineraryCard
          itinerary={itinerary({
            price: {
              amount: null,
              currency: "USD",
              status: "UNKNOWN",
              segment_count: 1,
              verified_at: null,
              disclaimer: "Price could not be estimated.",
            },
          })}
        />
      </ul>,
    );
    expect(screen.getByText("Price unavailable")).toBeInTheDocument();
    expect(screen.queryByText(/Estimated: Unavailable/)).not.toBeInTheDocument();
  });

  it("shows a cross-midnight one-stop itinerary accessibly", async () => {
    const oneStop = itinerary({
      itinerary_id: "iti-one-stop",
      arrival_at: "2026-08-05T01:10:00-07:00",
      connection_count: 1,
      total_layover_minutes: 60,
      price: { ...itinerary().price, amount: "29.82", segment_count: 2 },
      segments: [
        itinerary().segments[0],
        {
          sequence: 2,
          carrier: "F9",
          flight_number: "5678",
          origin: "DEN",
          destination: "LAS",
          departure_at: "2026-08-04T23:55:00-06:00",
          arrival_at: "2026-08-05T01:10:00-07:00",
          duration_minutes: 135,
        },
      ],
    });
    const { container } = render(<ul><ItineraryCard itinerary={oneStop} /></ul>);
    expect(screen.getByText("● 1 stop")).toBeInTheDocument();
    expect(screen.getByText(/arrives 2026-08-05/)).toBeInTheDocument();
    expect(screen.getByText(/Layover 1h/)).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });
});
