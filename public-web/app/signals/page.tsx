import type { Metadata } from "next";
import Link from "next/link";
import { getSignals, siteUrl } from "@/lib/api";
import { Icon } from "@/components/icon";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "XAUUSD Gold Signals", description: "Latest approved XAUUSD levels with transparent risk context.", alternates: { canonical: siteUrl("/signals") }, openGraph: { title: "XAUUSD Gold Signals | VenusRealm", description: "Approved public gold signals with entries, targets and explicit risk context.", url: siteUrl("/signals") } };

const shown = (value: string | number | null | undefined) => value == null || value === "" ? "—" : String(value);
const date = (value?: string | null) => value ? new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "Time unavailable";

export default async function SignalsPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams;
  const query = new URLSearchParams({ page: String(params.page || "1"), status: String(params.status || "all"), direction: String(params.direction || "all"), symbol: String(params.symbol || "") });
  const data = await getSignals(query);
  const pageHref = (page: number) => `?${new URLSearchParams({ ...Object.fromEntries(query), page: String(page) })}`;
  return <section className="signals-page">
    <header className="page-heading"><span className="eyebrow">GOLD SIGNAL DESK</span><h1>XAUUSD levels, with risk in full view.</h1><p>Only approved, published signal records appear here. VenusRealm never inserts placeholder entries, targets or performance claims.</p></header>
    <form className="public-signal-filters" method="get" aria-label="Filter public signals"><label>Status<select name="status" defaultValue={query.get("status") || "all"}><option value="all">All public statuses</option>{["PUBLISHED","ACTIVE","TARGET_HIT","STOPPED","CANCELLED","EXPIRED","CLOSED"].map(value => <option key={value}>{value}</option>)}</select></label><label>Direction<select name="direction" defaultValue={query.get("direction") || "all"}><option value="all">BUY & SELL</option><option>BUY</option><option>SELL</option></select></label><label>Symbol<input name="symbol" defaultValue={query.get("symbol") || ""} placeholder="XAUUSD" maxLength={20} /></label><button className="button button-dark" type="submit">Apply filters</button></form>
    <div className="signals-status"><p>{data.total} published signal{data.total === 1 ? "" : "s"}</p><p>Last updated: {date(data.items[0]?.updated_at || data.items[0]?.published_at)}</p></div>
    {data.items.length ? <div className="public-signal-grid">{data.items.map((signal, index) => <article className="public-signal-card" key={signal.public_id || `${signal.symbol}-${index}`}><div className="public-signal-card-head"><div><span>{date(signal.published_at)}</span><h2>{signal.symbol || "Market signal"}</h2></div><span className={`public-direction ${(signal.direction || "").toLowerCase()}`}>{signal.direction === "SELL" ? "↓ SELL" : "↑ BUY"}<small>{signal.status || "PUBLISHED"}</small></span></div><dl><div><dt>Timeframe</dt><dd>{signal.timeframe || "—"}</dd></div><div><dt>Entry</dt><dd>{shown(signal.entry_price)}</dd></div><div><dt>Stop loss</dt><dd>{shown(signal.stop_loss)}</dd></div><div><dt>Targets</dt><dd>{[signal.target_1,signal.target_2,signal.target_3,signal.target_4].filter(value => value != null).join(" · ") || "—"}</dd></div></dl>{signal.public_id ? <Link className="text-link" href={`/signals/${signal.public_id}`}>View signal details →</Link> : <span className="legacy-note">Detail view is unavailable for this legacy public record.</span>}</article>)}</div> : <div className="empty-state"><Icon name="clock" size={26}/><div><h2>No verified public signals</h2><p>No approved signal matches these filters, or the public API is temporarily unavailable. No synthetic values are shown.</p></div></div>}
    {data.pages > 1 && <nav className="pagination" aria-label="Signal pages">{data.page > 1 && <Link href={pageHref(data.page - 1)}>Previous</Link>}<span className="current">{data.page}</span>{data.page < data.pages && <Link href={pageHref(data.page + 1)}>Next</Link>}</nav>}
    <aside className="risk article-risk"><strong>Risk warning:</strong> Signals are educational information, not financial advice. Confirm prices independently and define your own loss limit before considering any market action.</aside>
  </section>;
}
