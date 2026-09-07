import Link from "next/link";
import type { Category, ContentSummary, Paginated } from "@/lib/content-api";
import { ContentActions } from "./content-actions";

const shortDate = (value: string | null) => value
  ? new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value))
  : "—";
const number = (value: number) => new Intl.NumberFormat("en-IN").format(value);

export function ContentList({ kind, data, categories, search, status, category, sort, publicWebsiteUrl }: {
  kind: "posts" | "pages"; data: Paginated<ContentSummary>; categories: Category[];
  search: string; status: string; category: string; sort: string; publicWebsiteUrl?: string;
}) {
  const isPosts = kind === "posts";
  const label = isPosts ? "Blog Studio" : "Pages";
  const stats = data.stats || { total: data.total, published: 0, drafts: 0, scheduled: 0, trashed: 0, total_views: 0 };
  const query = new URLSearchParams({ search, status, sort });
  if (category) query.set("category", category);
  const pageHref = (page: number) => `?${new URLSearchParams({ ...Object.fromEntries(query), page: String(page) })}`;
  return <>
    <section className="page-heading studio-heading">
      <div><span className="eyebrow">CONTENT WORKSPACE</span><h1>{label}</h1><p>{isPosts ? "Create, optimize and publish your market coverage from one focused workspace." : "Manage the site’s evergreen public pages."}</p></div>
      <Link className="primary-button button-with-icon" href={`/admin/${kind}/new`}><span aria-hidden="true">＋</span> New {isPosts ? "Post" : "Page"}</Link>
    </section>
    {isPosts && <section className="studio-kpis" aria-label="Post totals">
      {[
        ["Total Posts", stats.total, "stack"], ["Published", stats.published, "check"],
        ["Drafts", stats.drafts, "pencil"], ["Scheduled", stats.scheduled, "clock"],
        ["Trashed", stats.trashed, "trash"], ["Total Views", stats.total_views, "eye"]
      ].map(([name, value, icon]) => <article className="studio-kpi" key={String(name)}>
        <span className={`kpi-icon ${icon}`} aria-hidden="true">{icon === "check" ? "✓" : icon === "clock" ? "◷" : icon === "eye" ? "◉" : icon === "trash" ? "⌫" : icon === "pencil" ? "✎" : "▤"}</span>
        <div><small>{name}</small><strong>{number(Number(value))}</strong></div>
      </article>)}
    </section>}
    <section className="content-panel">
      <div className="content-panel-head"><div><h2>{isPosts ? "All posts" : "All pages"}</h2><p>{number(data.total)} result{data.total === 1 ? "" : "s"} in the current view</p></div></div>
      <form className="filter-bar studio-filters" method="get">
        <label className="search-field"><span className="sr-only">Search</span><span aria-hidden="true">⌕</span><input name="search" defaultValue={search} placeholder={`Search ${isPosts ? "title, slug or keyword" : "pages"}`} /></label>
        <label><span className="sr-only">Status</span><select name="status" defaultValue={status}><option value="all">All statuses</option><option value="published">Published</option><option value="draft">Drafts</option>{isPosts && <><option value="scheduled">Scheduled</option><option value="trash">Trashed</option></>}</select></label>
        <label><span className="sr-only">Category</span><select name="category" defaultValue={category}><option value="">All categories</option>{categories.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
        <label><span className="sr-only">Sort</span><select name="sort" defaultValue={sort}><option value="updated_desc">Recently updated</option><option value="updated_asc">Oldest updated</option><option value="title_asc">Title A–Z</option><option value="title_desc">Title Z–A</option><option value="published_desc">Recently published</option></select></label>
        <button className="secondary-button">Apply filters</button>
        {(search || status !== "all" || category || sort !== "updated_desc") && <Link className="clear-filter" href={`/admin/${kind}`}>Clear</Link>}
      </form>
      {data.items.length ? <div className="table-wrap"><table className="cms-table studio-table">
        <thead><tr><th><input type="checkbox" disabled aria-label="Select all posts" /></th><th>Post</th><th>ID</th><th>Category</th><th>Status</th><th>Views</th><th>SEO</th><th>Slug</th><th>Author</th><th>Updated</th><th>Actions</th></tr></thead>
        <tbody>{data.items.map(item => {
          const previewUrl = publicWebsiteUrl && item.status === "published" ? `${publicWebsiteUrl}/${isPosts ? "blog" : "page"}/${encodeURIComponent(item.slug)}` : undefined;
          const seoChecked = Boolean(item.seo_checked);
          const seoScore = seoChecked && typeof item.seo_score === "number" ? item.seo_score : null;
          const seoIssues = Array.isArray(item.seo_issues) ? item.seo_issues : [];
          return <tr key={item.id}>
            <td><input type="checkbox" aria-label={`Select ${item.title}`} disabled /></td>
            <td className="post-cell"><Link className="post-thumbnail" href={`/admin/${kind}/${item.id}/edit`} aria-label={`Edit ${item.title}`} style={item.featured_image ? { backgroundImage: `url(${item.featured_image})` } : undefined}>{!item.featured_image && <span aria-hidden="true">VR</span>}</Link><div><Link className="post-title" href={`/admin/${kind}/${item.id}/edit`}>{item.title}</Link><small>{item.scheduled_at && item.status === "scheduled" ? `Scheduled ${shortDate(item.scheduled_at)}` : item.content_type.replace("_", " ")}</small></div></td>
            <td className="numeric">#{item.id}</td><td>{item.category || "Uncategorized"}</td>
            <td><span className={`status-badge ${item.status}`}><i aria-hidden="true" />{item.status}</span></td>
            <td className="numeric">{number(item.views || 0)}</td><td className="seo-report-cell">
              {seoScore === null
                ? <><span className="seo-score unchecked" title="SEO validation has not been run">—</span>
                    <Link className="seo-report-link" href={`/admin/${kind}/${item.id}/edit#post-workbench`}>Run SEO check</Link></>
                : <><span className={`seo-score ${seoScore >= 80 ? "good" : seoScore >= 50 ? "fair" : "low"}`} title="Latest saved SEO validation score">{seoScore}</span>
                    <details className="seo-mini-report">
                      <summary>{seoIssues.length ? `View ${seoIssues.length} issue${seoIssues.length === 1 ? "" : "s"}` : "SEO report"}</summary>
                      {seoIssues.length
                        ? <ul>{seoIssues.slice(0, 4).map((issue, index) =>
                            <li key={`${issue.code}-${index}`}><b>{issue.points_lost ? `−${issue.points_lost}` : "Info"}</b> {issue.message}</li>
                          )}</ul>
                        : <p>No saved deductions.</p>}
                      <Link href={`/admin/${kind}/${item.id}/edit#post-workbench`}>Open full report</Link>
                    </details></>
              }
            </td>
            <td><code className="slug-cell">/{item.slug}</code></td><td className="author-cell">{item.author || "System"}</td><td className="date-cell">{shortDate(item.updated_at)}</td>
            <td><ContentActions kind={kind} id={item.id} status={item.status} previewUrl={previewUrl} previewLabel="Open preview" compact /></td>
          </tr>})}</tbody>
      </table></div> : <section className="state-panel empty-table"><strong>No {isPosts ? "posts" : "pages"} found</strong><p>Create a draft or change the current filters.</p></section>}
      <nav className="pagination" aria-label="Pagination"><span>Page {data.page} of {data.pages}</span><div>{data.page > 1 ? <Link href={pageHref(data.page - 1)}>← Previous</Link> : <span aria-disabled="true">← Previous</span>}{data.page < data.pages ? <Link href={pageHref(data.page + 1)}>Next →</Link> : <span aria-disabled="true">Next →</span>}</div></nav>
    </section>
  </>;
}
