import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { MemberSignalDetail } from "@/components/member-signal-detail";
import { getSignalDetail, siteUrl } from "@/lib/api";

const date = (value?: string | null) =>
  value
    ? new Intl.DateTimeFormat("en", { dateStyle: "long", timeStyle: "short" }).format(new Date(value))
    : "Not available";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ publicId: string }>;
}): Promise<Metadata> {
  const { publicId } = await params;
  const signal = await getSignalDetail(publicId);
  if (!signal) return { title: "Signal not found" };
  const title = `${signal.symbol || "Gold"} protected signal`;
  const description = "Published Gold Signal metadata. Actionable levels require verified paid-member access.";
  return {
    title,
    description,
    alternates: { canonical: siteUrl(`/signals/${publicId}`) },
    openGraph: {
      title,
      description,
      url: siteUrl(`/signals/${publicId}`),
      type: "article",
    },
  };
}

export default async function SignalDetailPage({
  params,
}: {
  params: Promise<{ publicId: string }>;
}) {
  const { publicId } = await params;
  const signal = await getSignalDetail(publicId);
  if (!signal) notFound();

  return (
    <article className="signal-detail">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link href="/">Home</Link><span>/</span>
        <Link href="/signals">Signals</Link><span>/</span>
        <span>{signal.symbol || "Gold signal"}</span>
      </nav>

      <header className="signal-detail-header">
        <span className="eyebrow">PROTECTED SIGNAL · {signal.status || "PUBLISHED"}</span>
        <h1>{signal.symbol || "XAUUSD"} member signal</h1>
        <p>
          Direction, entry, stop loss, targets and member analysis are protected.
          Sign in with a verified paid membership to load the actionable record.
        </p>
        <div className="article-meta">
          <span>Published {date(signal.published_at)}</span>
          <span>Updated {date(signal.updated_at)}</span>
          <span>Risk label: {signal.risk_level || "Not labelled"}</span>
        </div>
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
