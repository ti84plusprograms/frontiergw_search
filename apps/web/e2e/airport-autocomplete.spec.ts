import { expect, test } from "@playwright/test";

test("selects ATL from airport autocomplete", async ({ page }) => {
  await page.route("**/api/v1/airports**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            code: "ATL",
            name: "Hartsfield-Jackson Atlanta International Airport",
            city: "Atlanta",
            state_or_region: "Georgia",
            country_code: "US",
            timezone: "America/New_York",
            latitude: 33.6407,
            longitude: -84.4277,
          },
        ],
      }),
    });
  });

  await page.goto("/");
  const airportInput = page.getByRole("combobox", { name: "Departure airport" });
  await airportInput.fill("atl");
  await expect(page.getByRole("option")).toContainText("ATL — Atlanta");
  await page.getByRole("option").getByRole("button").click();
  await expect(airportInput).toHaveValue("ATL — Atlanta");
});
