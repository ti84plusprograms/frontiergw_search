import { SearchForm } from "@/components/SearchForm";
import { parseSearchParams } from "@/lib/url/searchParams";

type PageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function Home({ searchParams }: PageProps) {
  const raw = await searchParams;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(raw)) {
    if (typeof value === "string") params.set(key, value);
    else if (Array.isArray(value)) value.forEach((item) => params.append(key, item));
  }
  const initial = parseSearchParams(params);
  return <SearchForm initial={initial ?? undefined} />;
}
