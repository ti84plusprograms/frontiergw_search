import { expect, test } from "@playwright/test";

const API = process.env.FULL_STACK_API_URL ?? "http://localhost:8000";
const DIRECT = {
  origin: "ATL",
  departure_date: "2026-08-04",
  max_connections: 0,
};

test("real stack serves airport, status, direct search, and cached repeat", async ({
  page,
  request,
}) => {
  const external: string[] = [];
  page.on("request", (outbound) => {
    const host = new URL(outbound.url()).hostname;
    if (!["localhost", "127.0.0.1"].includes(host))
      external.push(outbound.url());
  });

  const airport = await request.get(
    `${API}/api/v1/airports?query=Atlanta&limit=5`,
  );
  expect(airport.ok()).toBeTruthy();
  expect((await airport.json()).items[0].code).toBe("ATL");
  expect(airport.headers()["x-request-id"]).toBeTruthy();

  const status = await request.get(`${API}/api/v1/schedules/status`);
  expect(status.ok()).toBeTruthy();
  expect((await status.json()).active).toBe(true);

  const first = await request.post(`${API}/api/v1/search`, { data: DIRECT });
  const second = await request.post(`${API}/api/v1/search`, { data: DIRECT });
  expect(first.ok()).toBeTruthy();
  expect(second.ok()).toBeTruthy();
  const firstBody = await first.json();
  const secondBody = await second.json();
  expect(firstBody.result_count).toBeGreaterThan(0);
  expect(secondBody.results).toEqual(firstBody.results);
  expect(secondBody.search_id).not.toBe(firstBody.search_id);
  expect(secondBody.generated_at).not.toBe(firstBody.generated_at);

  await page.goto("/");
  await page.getByRole("combobox", { name: "Origin airport" }).fill("ATL");
  await page.getByRole("option", { name: /ATL.*Atlanta/ }).click();
  await page.getByLabel("Departure date").fill("2026-08-04");
  await page.getByRole("radio", { name: "Direct only" }).check();
  await page.getByRole("button", { name: "Search destinations" }).click();
  await expect(
    page.getByRole("heading", { name: "Denver (DEN)" }),
  ).toBeVisible();
  await expect(
    page.getByText("Availability not checked").first(),
  ).toBeVisible();
  expect(external).toEqual([]);
});

test("real API handles no results, malformed input, and correlated errors", async ({
  request,
}) => {
  const empty = await request.post(`${API}/api/v1/search`, {
    data: { origin: "ORL", departure_date: "2026-08-04", max_connections: 0 },
  });
  expect(empty.ok()).toBeTruthy();
  expect((await empty.json()).result_count).toBe(0);

  const invalid = await request.post(`${API}/api/v1/search`, {
    data: { ...DIRECT, max_connections: 2 },
    headers: { "X-Request-ID": "fullstack-validation-1" },
  });
  expect(invalid.status()).toBe(422);
  expect(invalid.headers()["x-request-id"]).toBe("fullstack-validation-1");
  expect((await invalid.json()).error.request_id).toBe(
    "fullstack-validation-1",
  );
});

test("controlled search burst returns the standard rate-limit response", async ({
  request,
}) => {
  let limited = null;
  for (let index = 0; index < 40; index += 1) {
    const response = await request.post(`${API}/api/v1/search`, {
      data: DIRECT,
    });
    if (response.status() === 429) {
      limited = response;
      break;
    }
  }
  expect(
    limited,
    "staging SEARCH_RATE_LIMIT_PER_MINUTE must be <= 40",
  ).not.toBeNull();
  expect(limited!.headers()["retry-after"]).toBeTruthy();
  expect((await limited!.json()).error.code).toBe("RATE_LIMITED");
});
