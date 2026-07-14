import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ShareControls } from "@/components/share-controls";
import { getSignalDetail, siteUrl } from "@/lib/api";

const shown = (value: string | number | null | undefined) => value == null || value === "" ? "—" : String(value);
const date = (value?: string | null) => value ? new Intl.DateTimeFormat("en", { dateStyle: "long", timeStyle: "short" }).format(new Date(value)) : "Not available";

export async function generateMetadata({ params }: { params: Promise<{ publicId: string }> }): Promise<Metadata> {
  const { publicId } = await params; const signal = await getSignalDetail(publicId);
  if (!signal) return { title: "Signal not found" };
  const title = `${signal.symbol} ${signal.direction} signal`;
  const description = signal.analysis_summary || `Published ${signal.symbol} signal with entry, targets and risk context.`;
  return { title, description, alternates: { canonical: siteUrl(`/signals/${publicId}`) }, openGraph: { title, description, url: siteUrl(`/signals/${publicId}`), type: "article" } };
}

export default async function SignalDetailPage({ params }: { params: Promise<{ publicId: string }> }) {
  const { publicId } = await params; const signal = await getSignalDetail(publicId); if (!signal) notFound();
  const title = `${signal.symbol} ${signal.direction} signal`;
  return <article className="signal-detail"><nav className="breadcrumb" aria-label="Breadcrumb"><Link href="/">Home</Link><span>/</span><Link href="/signals">Signals</Link><span>/</span><span>{signal.symbol}</span></nav><header className="signal-detail-header"><span className="eyebrow">PUBLISHED SIGNAL · {signal.status}</span><h1>{title}</h1><p>{signal.analysis_summary || "Published market levels with explicit risk controls."}</p><div className="article-meta"><span>Published {date(signal.published_at)}</span><span>Updated {date(signal.updated_at)}</span><span>Risk: {signal.risk_level || "Not labelled"}</span></div></header><ShareControls title={title} url={siteUrl(`/signals/${publicId}`)} />
    <section className="signal-level-section" aria-labelledby="signal-levels"><h2 id="signal-levels">Market levels</h2><div className="signal-level-grid"><div><span>Direction</span><strong>{signal.direction}</strong></div><div><span>Entry</span><strong>{shown(signal.entry_price)}</strong></div><div><span>Stop loss</span><strong>{shown(signal.stop_loss)}</strong></div><div><span>Timeframe</span><strong>{shown(signal.timeframe)}</strong></div></div><div className="target-strip" aria-label="Targets">{[signal.target_1,signal.target_2,signal.target_3,signal.target_4].filter(value => value != null).map((target, index) => <div key={index}><span>Target {index + 1}</span><strong>{shown(target)}</strong></div>)}</div></section>
    <section className="signal-analysis" aria-labelledby="signal-analysis"><h2 id="signal-analysis">Published analysis</h2><div>{signal.technical_reason && <section aria-labelledby="technical-context"><h3 id="technical-context">Technical context</h3><p>{signal.technical_reason}</p></section>}{signal.astrology_reason && <section aria-labelledby="astrology-context"><h3 id="astrology-context">Astrology context</h3><p>{signal.astrology_reason}</p></section>}{!signal.technical_reason && !signal.astrology_reason && <p>No extended analysis was published for this signal.</p>}</div></section>
    <section className="signal-risk-note" aria-labelledby="signal-risk"><h2 id="signal-risk">Risk context</h2><p>{signal.risk_note || "No trade is guaranteed. Confirm market prices independently and use a loss limit appropriate to your circumstances."}</p></section>
    <aside className="risk article-risk"><strong>Global financial-risk disclaimer:</strong> Signals and market analysis are educational information, not financial advice. Leveraged trading can result in substantial loss. Past outcomes do not predict future results.</aside>
  </article>;
}
