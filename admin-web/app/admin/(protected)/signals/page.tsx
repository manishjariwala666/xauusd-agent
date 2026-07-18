import { cookies } from "next/headers";
import { SignalsDashboard } from "@/components/signals-dashboard";
import { fetchSignals } from "@/lib/signals-api";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

export default async function SignalsPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams;
  const filters = { page: String(params.page || "1"), page_size: "20", search: String(params.search || ""), status: String(params.status || "all"), direction: String(params.direction || "all"), symbol: String(params.symbol || ""), timeframe: String(params.timeframe || "all"), date_filter: String(params.date_filter || "all"), sort: String(params.sort || "updated_desc") };
  const token = (await cookies()).get(ADMIN_SESSION_COOKIE)?.value || "";
  const data = await fetchSignals(new URLSearchParams(filters), token);
  if (!data) return <section className="state-panel error-state"><strong>Signals could not be loaded.</strong><p>Check the isolated staging API and try again.</p></section>;
  return <SignalsDashboard data={data} filters={filters} />;
}
