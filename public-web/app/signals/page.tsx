import type { Metadata } from "next";
import Link from "next/link";
import { MemberSignalPanel } from "@/components/member-signal-panel";

export const metadata: Metadata = {
  title: "Gold Signals | Paid Member Access",
  description: "VenusRealm Gold Signals are reserved for verified paid members. Public pages explain access without rendering live signal data.",
};

export default function SignalsPage() {
  return <main className="signals-page">
    <section className="signal-hero">
      <span className="eyebrow">GOLD SIGNALS · PREMIUM</span>
      <h1>Gold signals for verified paid members</h1>
      <p>Live direction, timeframe, entry, stop loss, targets, timestamps and protected analysis are not rendered on the public page. They are requested only after authenticated paid-member access is verified.</p>
      <div className="hero-actions"><Link className="button primary" href="/login">Member login</Link><Link className="button secondary" href="/signup">Create account</Link><Link className="button secondary" href="/contact">Contact support</Link></div>
    </section>

    <MemberSignalPanel />

    <section className="premium-access-explainer" aria-labelledby="premium-access-title">
      <div className="section-heading"><div><span className="eyebrow">PROTECTED ACCESS</span><h2 id="premium-access-title">What stays inside the member desk</h2></div><p>The public page explains the product only. It does not call or render live Gold Signal data.</p></div>
      <div className="signal-grid">
        <article className="signal-card"><h3>Direction & timeframe</h3><p>Available only after verified paid-member access.</p></article>
        <article className="signal-card"><h3>Entry, stop loss & targets</h3><p>Protected trade levels remain inside the authenticated member flow.</p></article>
        <article className="signal-card"><h3>Live signal timing & analysis</h3><p>Signal timestamps and member analysis are not shown to public visitors.</p></article>
      </div>
    </section>

    <aside className="risk article-risk"><strong>Financial-risk disclaimer:</strong> Signals and market analysis are educational information, not financial advice. Leveraged trading can result in substantial loss. Past outcomes do not predict future results.</aside>
  </main>;
}
