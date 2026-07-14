import type { Metadata } from "next";
import Link from "next/link";
import { getResults } from "@/lib/api";

export const metadata: Metadata = { title: "Verified Results", description: "Compliance-reviewed VenusRealm trade outcome records." };
export const revalidate = 120;

export default async function Page({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const params = await searchParams;
  const query = new URLSearchParams({ page: String(params.page || "1"), symbol: String(params.symbol || ""), outcome: String(params.outcome || "all") });
  const data = await getResults(query);
  return <section>
    <header className="page-heading"><span className="eyebrow">EVIDENCE-LED REPORTING</span><h1>Verified results, without inflated claims.</h1><p>Every public record requires documented evidence, privacy redaction, independent review and compliance approval. Past results do not guarantee future performance.</p></header>
    <section aria-labelledby="method"><h2 id="method">Verification methodology</h2><p>Results use stored entry and exit prices. BUY points equal exit minus entry; SELL points equal entry minus exit. Account profit, ROI and win rate are omitted.</p></section>
    <form className="public-filters" method="get" aria-label="Verified result filters"><label>Symbol<input name="symbol" maxLength={30} defaultValue={params.symbol || ""} placeholder="XAUUSD" /></label><label>Outcome<select name="outcome" defaultValue={params.outcome || "all"}><option value="all">All outcomes</option>{["TARGET_HIT", "STOPPED", "CLOSED", "CANCELLED"].map(value => <option key={value}>{value.replaceAll("_", " ")}</option>)}</select></label><button>Filter</button></form>
    {data.items.length ? <div className="content-grid">{data.items.map(item => <article className="content-card" key={item.public_id}><div className="card-content"><span className="card-category">VERIFIED · {item.lifecycle_outcome}</span><h2><Link href={`/results/${item.public_id}`}>{item.symbol} {item.direction}</Link></h2><p>{item.public_summary}</p><dl><div><dt>Result</dt><dd>{item.result_points} {item.result_unit}</dd></div><div><dt>Verified</dt><dd>{new Date(item.verified_at).toLocaleDateString("en-IN")}</dd></div></dl></div></article>)}</div> : <div className="empty-state"><div><h2>No verified public results</h2><p>{data.fallback ? "The results service is unavailable. No synthetic or cached claims are shown." : "No record currently satisfies every evidence, review, privacy and publication gate."}</p></div></div>}
    <nav className="pagination" aria-label="Verified result pages">{data.page > 1 && <Link href={`?page=${data.page - 1}&symbol=${encodeURIComponent(params.symbol || "")}&outcome=${params.outcome || "all"}`}>Previous</Link>}<span>Page {data.page} of {data.pages}</span>{data.page < data.pages && <Link href={`?page=${data.page + 1}&symbol=${encodeURIComponent(params.symbol || "")}&outcome=${params.outcome || "all"}`}>Next</Link>}</nav>
    <aside className="risk-banner"><strong>Risk notice</strong><p>Past outcomes do not predict future performance. Trading gold and leveraged products can result in substantial loss.</p></aside>
  </section>;
}
