import type { Metadata } from "next";
import Link from "next/link";
import { getAnnouncements } from "@/lib/api";

export const metadata: Metadata = { title: "Announcements", description: "Published VenusRealm platform and market notices." };
export const revalidate = 120;

export default async function Page({ searchParams }: { searchParams: Promise<Record<string, string | undefined>> }) {
  const params = await searchParams;
  const query = new URLSearchParams({ page: String(params.page || "1"), kind: String(params.kind || "all"), priority: String(params.priority || "all") });
  const data = await getAnnouncements(query);
  return <section className="publication-page">
    <header className="page-heading publication-hero">
      <span className="eyebrow">PLATFORM UPDATES</span>
      <h1>Announcements, clearly documented.</h1>
      <p>Only approved, published and unexpired notices appear here.</p>
    </header>

    <form className="publication-filters" method="get" aria-label="Announcement filters">
      <label>Type<select name="kind" defaultValue={params.kind || "all"}><option value="all">All types</option>{["PLATFORM_UPDATE", "MARKET_NOTICE", "SIGNAL_UPDATE", "SERVICE_NOTICE", "EDUCATION", "EVENT", "GENERAL"].map(value => <option key={value}>{value.replaceAll("_", " ")}</option>)}</select></label>
      <label>Priority<select name="priority" defaultValue={params.priority || "all"}><option value="all">All priorities</option>{["NORMAL", "IMPORTANT", "URGENT"].map(value => <option key={value}>{value}</option>)}</select></label>
      <button type="submit">Apply filters</button>
    </form>

    {data.items.length ? <div className="publication-grid">{data.items.map(item => <article className="publication-card" key={item.slug}>
      <div className="publication-card-meta"><span>{item.priority}</span><span>{item.type.replaceAll("_", " ")}</span></div>
      <h2><Link href={`/announcements/${item.slug}`}>{item.title}</Link></h2>
      <p>{item.summary}</p>
      <footer className="publication-card-footer"><time dateTime={item.published_at}>{new Date(item.published_at).toLocaleDateString("en-IN", { dateStyle: "medium" })}</time><Link href={`/announcements/${item.slug}`}>Read announcement <span aria-hidden="true">→</span></Link></footer>
    </article>)}</div> : <div className="empty-state publication-empty"><div><h2>No public announcements</h2><p>{data.fallback ? "The announcement service is unavailable. No cached or synthetic notices are shown." : "No approved announcement is currently published."}</p></div></div>}

    <nav className="pagination publication-pagination" aria-label="Announcement pages">{data.page > 1 && <Link href={`?page=${data.page - 1}&kind=${params.kind || "all"}&priority=${params.priority || "all"}`}>Previous</Link>}<span>Page {data.page} of {data.pages}</span>{data.page < data.pages && <Link href={`?page=${data.page + 1}&kind=${params.kind || "all"}&priority=${params.priority || "all"}`}>Next</Link>}</nav>
  </section>;
}
