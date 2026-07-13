import type { Metadata } from "next";
import { getSignals } from "@/lib/api";

export const metadata: Metadata = { title: "XAUUSD Signals", description: "Latest public XAUUSD market levels and risk context." };
export const dynamic = "force-dynamic";
export default async function SignalsPage() { const signals = await getSignals(); return <section><div className="page-heading"><small>LIVE TRADING TABLE</small><h1>XAUUSD Signals</h1><p>Fresh public rows are read directly from the trading table.</p></div>{signals.length ? <div className="table-wrap"><table><thead><tr><th>Time</th><th>Direction</th><th>Entry</th><th>Targets</th><th>Stop Loss</th></tr></thead><tbody>{signals.map((signal, index) => <tr key={signal.id || index}><td>{signal.signal_time || "—"}</td><td>{signal.signal_type || "WATCH"}</td><td>{signal.price ?? "—"}</td><td>{[signal.target_1, signal.target_2, signal.target_3].filter(Boolean).join(" · ") || "—"}</td><td>{signal.stop_loss ?? "—"}</td></tr>)}</tbody></table></div> : <div className="empty-state">No public signal rows are available right now.</div>}<div className="risk"><b>Risk warning:</b> Signals are informational and not financial advice.</div></section>; }
