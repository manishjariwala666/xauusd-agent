import { cookies } from "next/headers";

import { SignalsDashboard } from "@/components/signals-dashboard";
import { fetchSignals } from "@/lib/signals-api";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

type SearchParams = Promise<
  Record<string, string | string[] | undefined>
>;

function value(
  input: string | string[] | undefined,
  fallback: string,
): string {
  return Array.isArray(input)
    ? input[0] || fallback
    : input || fallback;
}

export default async function SignalsPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const params = await searchParams;

  const filters = {
    page: value(params.page, "1"),
    search: value(params.search, ""),
    status: value(params.status, "all"),
    direction: value(params.direction, "all"),
    symbol: value(params.symbol, ""),
    timeframe: value(params.timeframe, "all"),
    date_filter: value(params.date_filter, "all"),
    sort: value(params.sort, "updated_desc"),
  };

  const query = new URLSearchParams({
    ...filters,
    page_size: "20",
  });

  const token =
    (await cookies()).get(ADMIN_SESSION_COOKIE)?.value || "";

  const data = await fetchSignals(query, token);

  if (!data) {
    return (
      <section className="state-panel error-state">
        <strong>Signals could not be loaded.</strong>
        <p>Check the local admin API connection and try again.</p>
      </section>
    );
  }

  return (
    <SignalsDashboard
      data={data}
      filters={filters}
      basePath="/studio-v2/signals"
      readOnly
    />
  );
}
