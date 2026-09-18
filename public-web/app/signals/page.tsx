import type { Metadata } from "next";
import Link from "next/link";
import { MemberSignalPanel } from "@/components/member-signal-panel";
import { getSignals, siteUrl } from "@/lib/api";
import { Icon } from "@/components/icon";

export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "XAUUSD Gold Signals",
  description: "Protected XAUUSD Gold Signals for verified VenusRealm paid members.",
  alternates: { canonical: siteUrl("/signals") },
  openGraph: {
    title: "XAUUSD Gold Signals | VenusRealm",
    description: "Verified paid members can securely access published XAUUSD signal levels.",
    url: siteUrl("/signals"),
  },
};

const date = (value?: string | null) =>
  value
    ? new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value))
    : "Time unavailable";

export default async function SignalsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const query = new URLSearchParams({
    page: String(params.page || "1"),
    status: String(params.status || "all"),
    symbol: String(params.symbol || ""),
  });
  const data = await getSignals(query);
  const pageHref = (page: number) =>
    `?${new URLSearchParams({ ...Object.fromEntries(query), page: String(page) })}`;

  return (
    <section className="signals-page">
      <header className="page-heading">
        <span className="eyebrow">PREMIUM GOLD SIGNAL DESK</span>
        <h1>Gold signals for verified paid members</h1>
        <p>
          Public pages show only non-actionable publication metadata. Direction,
          entry, stop loss, targets and member analysis are returned only after
          authenticated paid-member verification. Available only after verified paid-member access.
        </p>
        <p><Link className="text-link" href="/contact">Need help with member access? Contact VenusRealm →</Link></p>
      </header>

      <MemberSignalPanel />

      <section aria-labelledby="public-signal-archive">
        <div className="section-heading compact-heading">
          <div>
            <span className="eyebrow">PUBLIC RECORD</span>
            <h2 id="public-signal-archive">Published signal availability</h2>
          </div>
          <p>Trading levels stay locked; this archive confirms only that a published record exists.</p>
        </div>

        <form className="public-signal-filters" method="get" aria-label="Filter signal availability">
          <label>
            Status
            <select name="status" defaultValue={query.get("status") || "all"}>
              <option value="all">All public statuses</option>
              {["PUBLISHED", "ACTIVE", "TARGET_HIT", "STOPPED", "CANCELLED", "EXPIRED", "CLOSED"].map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>
          <label>
            Symbol
            <input name="symbol" defaultValue={query.get("symbol") || ""} placeholder="XAUUSD" maxLength={20} />
          </label>
          <button className="button button-dark" type="submit">Apply filters</button>
        </form>

        <div className="signals-status">
          <p>{data.total} published signal record{data.total === 1 ? "" : "s"}</p>
          <p>Last updated: {date(data.items[0]?.updated_at || data.items[0]?.published_at)}</p>
        </div>

        {data.items.length ? (
          <div className="public-signal-grid">
            {data.items.map((signal, index) => (
              <article className="public-signal-card" key={signal.public_id || `${signal.symbol}-${index}`}>
                <div className="public-signal-card-head">
                  <div>
                    <span>{date(signal.published_at)}</span>
                    <h2>{signal.symbol || "Gold signal"}</h2>
                  </div>
                  <span className="public-direction">
                    🔒 MEMBER
                    <small>{signal.status || "PUBLISHED"}</small>
                  </span>
                </div>
                <dl>
                  <div><dt>Market</dt><dd>{signal.market || "GOLD"}</dd></div>
                  <div><dt>Timeframe</dt><dd>{signal.timeframe || "—"}</dd></div>
                  <div><dt>Member access</dt><dd>Required</dd></div>
                  <div><dt>Trading levels</dt><dd>Locked</dd></div>
                </dl>
                {signal.public_id ? (
                  <Link className="text-link" href={`/signals/${signal.public_id}`}>Open protected detail →</Link>
                ) : (
                  <span className="legacy-note">Protected detail is unavailable for this legacy record.</span>
                )}
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <Icon name="clock" size={26} />
            <div>
              <h2>No published signal record</h2>
              <p>No approved signal matches these public metadata filters.</p>
            </div>
          </div>
        )}

        {data.pages > 1 && (
          <nav className="pagination" aria-label="Signal pages">
            {data.page > 1 && <Link href={pageHref(data.page - 1)}>Previous</Link>}
            <span className="current">{data.page}</span>
            {data.page < data.pages && <Link href={pageHref(data.page + 1)}>Next</Link>}
          </nav>
        )}
      </section>

      <aside className="risk article-risk">
        <strong>Risk warning:</strong> Signals are educational information, not
        financial advice. Confirm prices independently and define your own loss
        limit before considering any market action.
      </aside>
    </section>
  );
}
