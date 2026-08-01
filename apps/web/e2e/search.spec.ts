import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Route } from "@playwright/test";

const AIRPORT = {
  code: "ATL",
  name: "Synthetic Atlanta Airport",
  city: "Atlanta",
  state_or_region: "Georgia",
  country_code: "US",
  timezone: "America/New_York",
};

function searchBody(results = true) {
  return {
    search_id: "srch-e2e",
    origin: { code: "ATL", city: "Atlanta", timezone: "America/New_York" },
    departure_date: "2026-08-04",
    generated_at: "2026-08-01T12:00:00+00:00",
    data_freshness: {
      schedule_source: "synthetic-e2e",
      schedule_version: "v1",
      schedule_updated_at: "2026-08-01T12:00:00+00:00",
      schedule_effective_start: "2026-08-01",
      schedule_effective_end: "2026-10-31",
      availability_checked_at: null,
    },
    result_count: results ? 1 : 0,
    results: results
      ? [
          {
            itinerary_id: "iti-e2e",
            origin: { code: "ATL", city: "Atlanta", country_code: "US" },
            destination: { code: "DEN", city: "Denver", country_code: "US" },
            departure_at: "2026-08-04T09:35:00-04:00",
            arrival_at: "2026-08-04T11:05:00-06:00",
            connection_count: 0,
            total_duration_minutes: 210,
            airborne_duration_minutes: 210,
            total_layover_minutes: 0,
            segments: [
              {
                sequence: 1,
                carrier: "F9",
                flight_number: "1234",
                origin: "ATL",
                destination: "DEN",
                departure_at: "2026-08-04T09:35:00-04:00",
                arrival_at: "2026-08-04T11:05:00-06:00",
                duration_minutes: 210,
              },
            ],
            price: {
              amount: "14.91",
              currency: "USD",
              status: "ESTIMATED",
              segment_count: 1,
              verified_at: null,
              disclaimer:
                "Final taxes, fees, and GoWild availability must be confirmed with Frontier.",
            },
            availability: {
              status: "NOT_CHECKED",
              checked_at: null,
              source: null,
              confidence: "LOW",
            },
            booking_url: null,
          },
        ]
      : [],
    warnings: [
      {
        code: results ? "AVAILABILITY_NOT_CHECKED" : "NO_MATCHING_ITINERARIES",
        message: results
          ? "GoWild availability has not been verified."
          : "No scheduled itineraries matched the selected criteria.",
      },
    ],
  };
}

async function installApi(page: Page, searchHandler?: (route: Route) => Promise<void>) {
  await page.route("http://localhost:8000/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/airports")) {
      await route.fulfill({ json: { items: [AIRPORT], count: 1 } });
      return;
    }
    if (url.pathname.endsWith("/schedules/status")) {
      await route.fulfill({
        json: {
          active: true,
          source: "synthetic-e2e",
          version: "v1",
          retrieved_at: "2026-08-01T12:00:00+00:00",
          effective_start: "2026-08-01",
          effective_end: "2026-10-31",
          route_count: 1,
          scheduled_flight_count: 1,
        },
      });
      return;
    }
    if (searchHandler) await searchHandler(route);
    else await route.fulfill({ json: searchBody() });
  });
}

test("keyboard search, URL restoration, sorting, and accessibility", async ({ page }) => {
  await installApi(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Where can you fly?" })).toBeVisible();

  const origin = page.getByRole("combobox", { name: "Origin airport" });
  await origin.fill("atl");
  await expect(page.getByRole("option", { name: /ATL.*Atlanta/ })).toBeVisible();
  await origin.press("Enter");
  await page.getByLabel("Departure date").fill("2026-08-04");
  await page.getByRole("radio", { name: "Direct only" }).focus();
  await page.keyboard.press("Space");
  await page.getByText("Advanced filters").focus();
  await page.keyboard.press("Enter");
  await page.getByLabel("Maximum estimated price (USD)").fill("20.50");
  await page.getByRole("button", { name: "Search destinations" }).press("Enter");

  await expect(page).toHaveURL(/\/results\?.*origin=ATL.*max_price=20.5/);
  await expect(page.getByRole("heading", { name: "Denver (DEN)" })).toBeVisible();
  await expect(page.getByText("Availability not checked")).toBeVisible();
  await expect(page.getByText(/Estimated: \$14.91/)).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);

  await page.getByLabel("Sort by").selectOption("DESTINATION");
  await expect(page).toHaveURL(/sort=DESTINATION/);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Denver (DEN)" })).toBeVisible();

  await page.getByRole("link", { name: "Modify this search" }).click();
  await expect(origin).toHaveValue("ATL");
  await expect(page.getByLabel("Departure date")).toHaveValue("2026-08-04");
  await page.getByRole("radio", { name: "Up to one stop" }).check();
  await page.getByRole("button", { name: "Search destinations" }).press("Enter");
  await expect(page).toHaveURL(/connections=1/);
  await expect(page.getByRole("heading", { name: "Denver (DEN)" })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("radio", { name: "Direct only" })).toBeChecked();
  await page.goForward();
  await expect(page).toHaveURL(/connections=1/);
  await expect(page.getByRole("heading", { name: "Denver (DEN)" })).toBeVisible();
});

test("no-results and backend validation errors are distinct", async ({ page }) => {
  let noResults = true;
  await installApi(page, async (route) => {
    if (noResults) await route.fulfill({ json: searchBody(false) });
    else {
      await route.fulfill({
        status: 422,
        json: {
          error: {
            code: "INVALID_REQUEST",
            message: "The request failed validation.",
            details: null,
            request_id: "req-e2e",
          },
        },
      });
    }
  });

  await page.goto("/results?origin=ATL&date=2026-08-04");
  await expect(page.getByText(/No Frontier destinations matched/)).toBeVisible();
  noResults = false;
  await page.reload();
  await expect(
    page.getByRole("alert").filter({ hasText: "We couldn't run that search" }),
  ).toBeVisible();
});

test("network failure and expected schedule outage have honest states", async ({ page }) => {
  let networkFailure = true;
  await installApi(page, async (route) => {
    if (networkFailure) await route.abort("failed");
    else {
      await route.fulfill({
        status: 503,
        json: {
          error: {
            code: "NO_ACTIVE_SCHEDULE",
            message: "No active schedule dataset is available.",
            details: null,
            request_id: "req-e2e",
          },
        },
      });
    }
  });

  await page.goto("/results?origin=ATL&date=2026-08-04");
  await expect(page.getByRole("alert").filter({ hasText: "Something went wrong" })).toBeVisible();
  networkFailure = false;
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Schedule data is temporarily unavailable" }),
  ).toBeVisible();
});

test("primary content does not overflow the mobile viewport", async ({ page, isMobile }) => {
  test.skip(!isMobile, "mobile-project assertion");
  await installApi(page);
  await page.goto("/results?origin=ATL&date=2026-08-04");
  await expect(page.getByRole("heading", { name: "Denver (DEN)" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(overflow).toBe(false);
});
