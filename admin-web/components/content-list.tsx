import Link from "next/link";
import type { ContentSummary, Paginated } from "@/lib/content-api";
import { ContentActions } from "./content-actions";

const date = (value: string | null) => value ? new Date(value).toLocaleDateString("en-IN") : "—";

export function ContentList({ kind, data, search, status, publicWebsiteUrl }: {
  kind: "posts" | "pages"; data: Paginated<ContentSummary>;
  search: string; status: string; publicWebsiteUrl?: string;
}) {
  const label = kind === "posts" ? "Posts" : "Pages";
  return <>
    <section className="page-heading cms-heading"><div><small>CONTENT CMS</small><h1>{label}</h1><p>Server-paginated drafts and published content.</p></div><Link className="primary-button" href={`/admin/${kind}/new`}>Add new</Link></section>
    <form className="filter-bar" method="get"><input name="search" defaultValue={search} placeholder={`Search ${label.toLowerCase()}`} /><select name="status" defaultValue={status}><option value="all">All</option><option value="draft">Draft</option><option value="published">Published</option>{kind === "posts" && <option value="trash">Trash</option>}</select><button className="secondary-button">Filter</button></form>
    {data.items.length ? <div className="table-wrap"><table className="cms-table"><thead><tr><th><span className="sr-only">Select</span></th><th>Title</th><th>Slug / preview</th><th>Category</th><th>Status</th><th>Author</th><th>Published</th><th>Updated</th><th>Actions</th></tr></thead><tbody>{data.items.map(item => <tr key={item.id}><td><input type="checkbox" aria-label={`Select ${item.title}`} disabled /></td><td><strong>{item.title}</strong></td><td><code>{item.slug}</code>{publicWebsiteUrl && item.status === "published" ? <><br /><a href={`${publicWebsiteUrl}/${kind === "posts" ? "blog" : "page"}/${encodeURIComponent(item.slug)}`} target="_blank" rel="noreferrer">Open preview</a></> : null}</td><td>{item.category || "Uncategorized"}</td><td><span className={`status-badge ${item.status}`}>{item.status}</span></td><td>{item.author || "System"}</td><td>{date(item.published_at)}</td><td>{date(item.updated_at)}</td><td><ContentActions kind={kind} id={item.id} status={item.status} /></td></tr>)}</tbody></table></div> : <section className="state-panel"><strong>No {label.toLowerCase()} found</strong><p>Create a draft or change the current filters.</p></section>}
    <nav className="pagination" aria-label="Pagination"><span>Page {data.page} of {data.pages} · {data.total} items</span>{data.page > 1 && <Link href={`?page=${data.page - 1}&search=${encodeURIComponent(search)}&status=${status}`}>Previous</Link>}{data.page < data.pages && <Link href={`?page=${data.page + 1}&search=${encodeURIComponent(search)}&status=${status}`}>Next</Link>}</nav>
  </>;
}
