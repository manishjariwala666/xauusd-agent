import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Premium Gold Signal | Member Access Required",
  description: "Actionable Gold Signal levels are protected VenusRealm paid-member content.",
  robots: { index: false, follow: false },
};

export default function SignalDetailPage() {
  return <main className="signal-detail">
    <nav className="breadcrumb" aria-label="Breadcrumb"><Link href="/">Home</Link><span>/</span><Link href="/signals">Signals</Link><span>/</span><span>Premium</span></nav>
    <header className="signal-detail-header">
      <span className="eyebrow">GOLD SIGNAL · PREMIUM</span>
      <h1>Paid member access required</h1>
      <p>Direction, entry, stop loss, targets and analysis are not available through a public signal URL. Verified paid members receive the complete signal inside the protected member experience.</p>
    </header>
    <section aria-labelledby="signal-levels"><h2 id="signal-levels">Protected signal levels</h2><p>Entry, stop loss and targets are hidden from unauthenticated public access.</p></section>
    <section aria-labelledby="signal-analysis"><h2 id="signal-analysis">Protected analysis</h2><div><section aria-labelledby="technical-context"><h3 id="technical-context">Technical context</h3><p>Available to verified paid members.</p></section><section aria-labelledby="astrology-context"><h3 id="astrology-context">Astrology context</h3><p>Available to verified paid members when included in the published signal.</p></section></div></section>
    <section aria-labelledby="signal-risk"><h2 id="signal-risk">Risk context</h2><p>Paid membership does not remove trading risk. Use independent price verification and appropriate loss limits.</p></section>
    <div className="hero-actions"><Link className="button primary" href="/pricing">View membership</Link><Link className="button secondary" href="/signals">Back to Gold Signals</Link></div>
    <aside className="risk article-risk"><strong>Financial-risk disclaimer:</strong> Signals and market analysis are educational information, not financial advice. Leveraged trading can result in substantial loss. Past outcomes do not predict future results.</aside>
  </main>;
}
