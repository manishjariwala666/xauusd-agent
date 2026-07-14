import Link from "next/link";
import type { SignalsPage } from "@/lib/signals-api";
import { SignalActions } from "./signal-actions";

const displayDate = (value: string | null) => value ? new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";
const price = (value: string | null) => value == null ? "—" : Number(value).toLocaleString("en-IN", { maximumFractionDigits: 6 });

export function SignalsDashboard({ data, filters }: { data: SignalsPage; filters: Record<string, string> }) {
  const stats = data.stats || { total: data.total };
  const kpis = [["Total", stats.total], ["Draft", stats.draft], ["Scheduled", stats.scheduled], ["Active", stats.active], ["Closed", stats.closed], ["Target Hit", stats.target_hit], ["Stopped", stats.stopped], ["Cancelled", stats.cancelled]];
  const queryFor = (page: number) => new URLSearchParams({ ...filters, page: String(page) }).toString();
  return <section className="signals-admin-page">
    <header className="studio-header"><div><span className="section-kicker">Publishing desk</span><h1>Signals Admin</h1><p>Create, review and control the lifecycle of public market signals.</p></div><Link className="primary-button" href="/admin/signals/new">New Signal</Link></header>
    <div className="signal-kpis" aria-label="Signal totals">{kpis.map(([label, value]) => <article key={label}><span>{label}</span><strong>{Number(value || 0).toLocaleString("en-IN")}</strong></article>)}</div>
    <section className="studio-panel signal-list-panel">
      <form className="signal-filters" method="get" aria-label="Signal filters">
        <label>Search<input name="search" defaultValue={filters.search} placeholder="Symbol, public ID or summary" /></label>
        <label>Status<select name="status" defaultValue={filters.status}><option value="all">All statuses</option>{["DRAFT","SCHEDULED","PUBLISHED","ACTIVE","TARGET_HIT","STOPPED","CANCELLED","EXPIRED","CLOSED","TRASHED"].map(value => <option key={value}>{value}</option>)}</select></label>
        <label>Direction<select name="direction" defaultValue={filters.direction}><option value="all">BUY & SELL</option><option>BUY</option><option>SELL</option></select></label>
        <label>Symbol<input name="symbol" defaultValue={filters.symbol} placeholder="XAUUSD" /></label>
        <label>Timeframe<input name="timeframe" defaultValue={filters.timeframe === "all" ? "" : filters.timeframe} placeholder="INTRADAY" /></label>
        <label>Date<select name="date_filter" defaultValue={filters.date_filter}><option value="all">Any date</option><option value="7d">Last 7 days</option><option value="30d">Last 30 days</option><option value="90d">Last 90 days</option></select></label>
        <label>Sort<select name="sort" defaultValue={filters.sort}><option value="updated_desc">Recently updated</option><option value="updated_asc">Oldest updated</option><option value="published_desc">Recently published</option></select></label>
        <button className="secondary-button" type="submit">Apply filters</button>
      </form>
      {data.items.length ? <div className="signal-table-wrap"><table className="signal-table"><thead><tr><th>Signal</th><th>Entry</th><th>Stop loss</th><th>Targets</th><th>Status</th><th>Published / updated</th><th>Actions</th></tr></thead><tbody>{data.items.map(item => <tr key={item.id}><td><Link href={`/admin/signals/${item.id}/edit`}><strong>{item.symbol}</strong></Link><span className={`direction-chip ${item.signal_type.toLowerCase()}`}>{item.signal_type === "BUY" ? "↑ BUY" : "↓ SELL"}</span><small>{item.timeframe}</small></td><td>{price(item.price)}</td><td>{price(item.stop_loss)}</td><td>{[item.target_1,item.target_2,item.target_3,item.target_4].filter(Boolean).map(price).join(" · ") || "—"}</td><td><span className="status-badge draft"><i />{item.lifecycle_status.replaceAll("_", " ")}</span></td><td><small>{displayDate(item.published_at)}<br />Updated {displayDate(item.updated_at)}</small></td><td><SignalActions id={item.id} state={item.lifecycle_status} /></td></tr>)}</tbody></table></div> : <div className="state-panel"><strong>No signals match these filters.</strong><p>Create a synthetic draft or broaden the current filters.</p></div>}
      <nav className="admin-pagination" aria-label="Signals pagination"><span>Page {data.page} of {data.pages}</span><div>{data.page > 1 && <Link href={`?${queryFor(data.page - 1)}`}>Previous</Link>}{data.page < data.pages && <Link href={`?${queryFor(data.page + 1)}`}>Next</Link>}</div></nav>
    </section>
  </section>;
}
