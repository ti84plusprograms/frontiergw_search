export type Airport = {
  code: string;
  name: string;
  city: string;
  state_or_region: string | null;
  country_code: string;
  timezone: string;
  latitude: number;
  longitude: number;
};

type AirportResponse = { items: Airport[] };

export async function searchAirports(
  query: string,
  fetchImpl: typeof fetch = fetch,
): Promise<Airport[]> {
  const normalizedQuery = query.trim();
  if (!normalizedQuery) return [];

  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  const url = new URL("airports", `${apiUrl.replace(/\/$/, "")}/`);
  url.searchParams.set("query", normalizedQuery);
  url.searchParams.set("limit", "10");

  const response = await fetchImpl(url.toString(), { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error("Airport search failed");

  const data = (await response.json()) as AirportResponse;
  return Array.isArray(data.items) ? data.items : [];
}
