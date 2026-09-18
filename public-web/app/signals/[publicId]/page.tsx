import type { Metadata } from "next";
import Link from "next/link";
import { MemberSignalDetail } from "@/components/member-signal-detail";
import { siteUrl } from "@/lib/api";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Protected Gold Signal",
  description: "Actionable XAUUSD Gold Signal details require verified paid-member access.",
  alternates: { canonical: siteUrl("/signals") },
  robots: { index: false, follow: false },
};

export default async function SignalDetailPage({
  params,
}: {
  params: Promise<{ publicId: string }>;
}) {
  const { publicId } = await params;

  return (
    <article className="signal-detail">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link href="/">Home</Link><span>/</span>
        <Link href="/signals">Signals</Link><span>/</span>
        <span>Protected detail</span>
      </nav>

      <header className="signal-detail-header">
        <span className="eyebrow">VERIFIED MEMBER ACCESS</span>
        <h1>Protected Gold Signal</h1>
        <p><strong>Paid member access required</strong></p>
        <p>
          Direction, entry, stop loss, targets and member analysis are never
          loaded from the public signal API. Verified paid members can load the
          published record below through the secure member session.
        </p>
      </header>

      <MemberSignalDetail publicId={publicId} />

      <section className="signal-risk-note" aria-labelledby="signal-risk">
        <h2 id="signal-risk">Risk context</h2>
        <p>
          No trade is guaranteed. Confirm market prices independently and use a
          loss limit appropriate to your circumstances.
        </p>
      </section>

      <aside className="risk article-risk">
        <strong>Global financial-risk disclaimer:</strong> Signals and market
        analysis are educational information, not financial advice. Leveraged
        trading can result in substantial loss. Past outcomes do not predict
        future results.
      </aside>
    </article>
  );
}
