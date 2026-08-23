import type { Metadata } from "next";
import Link from "next/link";
import { getSignals } from "@/lib/api";

export const metadata: Metadata = {
  title: "Gold Signals | Paid Member Access",
  description: "VenusRealm Gold Signals are available to verified paid members. Public pages show publication availability only; actionable levels remain protected.",
};

const date = (value?: string | null) => value
  ? new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value))
  : "Not available";

export default async function SignalsPage() {
  const data = await getSignals({ page: "1", page_size: "12", symbol: "XAUUSD" });
  const items = data?.items || [];

  return <main className="signals-page">
    <section className="signal-hero">
      <span className="eyebrow">GOLD SIGNALS · PREMIUM</span>
      <h1>Gold signals for verified paid members</h1>
      <p>Entry, direction, stop loss, targets and analysis are protected member content. This public page only confirms recent XAUUSD signal publication activity.</p>
      <div className="hero-actions">
        <Link className="button primary" href="/pricing">View membership</Link>
        <Link className="button secondary" href="/contact">Paid member support</Link>
      </div>
    </section>

    <section aria-labelledby="signal-availability">
      <div className="section-heading">
        <div><span className="eyebrow">PUBLIC AVAILABILITY</span><h2 id="signal-availability">Recent Gold Signal activity</h2></div>
        <p>Actionable trading levels are intentionally hidden until payment verification.</p>
      </div>
      {items.length ? <div className="signal-grid">
        {items.map((signal) => <article className="signal-card" key={signal.public_id}>
          <div className="signal-card-head"><span>{signal.symbol || "XAUUSD"}</span><span>{signal.status || "PUBLISHED"}</span></div>
          <h3>Premium Gold Signal</h3>
          <dl>
            <div><dt>Market</dt><dd>{signal.market || "GOLD"}</dd></div>
            <div><dt>Published</dt><dd>{date(signal.published_at)}</dd></div>
            <div><dt>Direction</dt><dd>Paid members only</dd></div>
            <div><dt>Entry / SL / Targets</dt><dd>Paid members only</dd></div>
          </dl>
          <Link href="/pricing">Unlock with verified membership →</Link>
        </article>)}
      </div> : <div className="empty-state"><h3>No public availability record right now</h3><p>Paid members receive protected signal access when a verified signal is published.</p></div>}
    </section>

    <aside className="risk article-risk"><strong>Financial-risk disclaimer:</strong> Signals and market analysis are educational information, not financial advice. Leveraged trading can result in substantial loss. Past outcomes do not predict future results.</aside>
  </main>;
}
