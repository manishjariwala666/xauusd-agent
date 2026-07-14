import type { Metadata } from "next";
import { getSignals, siteUrl } from "@/lib/api";
import { Icon } from "@/components/icon";
import { ShareControls } from "@/components/share-controls";

export const metadata: Metadata = { title: "XAUUSD Gold Signals", description: "Latest public XAUUSD levels with transparent risk context." };
export const dynamic = "force-dynamic";

export default async function SignalsPage() {
  const signals = await getSignals();
  return <section><header className="page-heading"><span className="eyebrow">GOLD SIGNAL DESK</span><h1>XAUUSD levels, with risk in full view.</h1><p>Public signal rows are loaded directly from the live desk. VenusRealm never inserts placeholder entries, targets or performance claims.</p></header><ShareControls title="VenusRealm XAUUSD Gold Signals" url={siteUrl("/signals")} />
    {signals.length ? <div className="signals-list">{signals.map((signal, index) => <article className="signal-row" id={signal.id ? String(signal.id) : undefined} key={signal.id || index}><div><span>{signal.signal_time || "Time unavailable"}</span><strong>{signal.symbol || "XAUUSD"} · {signal.signal_type || "WATCH"}</strong></div><dl><div><dt>Timeframe</dt><dd>{signal.timeframe || "—"}</dd></div><div><dt>Entry</dt><dd>{signal.price ?? "—"}</dd></div><div><dt>Targets</dt><dd>{[signal.target_1, signal.target_2, signal.target_3].filter((value) => value != null).join(" · ") || "—"}</dd></div><div><dt>Stop loss</dt><dd>{signal.stop_loss ?? "—"}</dd></div></dl></article>)}</div> : <div className="empty-state"><Icon name="clock" size={26}/><div><h3>No verified public signal is active</h3><p>Live data is unavailable or no row has been approved for publication. Refresh later; no synthetic values are shown.</p></div></div>}
    <div className="risk article-risk"><strong>Risk warning:</strong> Signals are educational information, not financial advice. Confirm prices independently and define your own loss limit before considering any market action.</div>
  </section>;
}
