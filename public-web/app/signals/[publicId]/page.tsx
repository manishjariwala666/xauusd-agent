import type { Metadata } from "next";
import Link from "next/link";
import { MemberSignalDetail } from "@/components/member-signal-detail";

export const metadata: Metadata = {
  title: "Premium Gold Signal | Member Access Required",
  description: "Actionable Gold Signal levels are protected VenusRealm paid-member content.",
  robots: { index: false, follow: false },
};

export default async function SignalDetailPage({ params }: { params: Promise<{ publicId: string }> }) {
  const { publicId } = await params;
  return <main className="signal-detail">
    <nav className="breadcrumb" aria-label="Breadcrumb"><Link href="/">Home</Link><span>/</span><Link href="/signals">Signals</Link><span>/</span><span>Premium</span></nav>
    <header className="signal-detail-header"><span className="eyebrow">GOLD SIGNAL · PREMIUM</span><h1>Protected Gold Signal</h1><p>Actionable levels are fetched only after server-side member and payment verification.</p></header>
    <MemberSignalDetail publicId={publicId} />
    <section aria-labelledby="signal-risk"><h2 id="signal-risk">Risk context</h2><p>Paid membership does not remove trading risk. Use independent price verification and appropriate loss limits.</p></section>
    <div className="hero-actions"><Link className="button secondary" href="/signals">Back to Gold Signals</Link></div>
    <aside className="risk article-risk"><strong>Financial-risk disclaimer:</strong> Signals and market analysis are educational information, not financial advice. Leveraged trading can result in substantial loss. Past outcomes do not predict future results.</aside>
  </main>;
}
