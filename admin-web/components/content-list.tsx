"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Category, ContentSummary, Paginated } from "@/lib/content-api";
import { ContentActions } from "./content-actions";

const shortDate = (value: string | null) => value
  ? new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value))
  : "—";
const number = (value: number) => new Intl.NumberFormat("en-IN").format(value);

export function ContentList({
  kind,
  data,
  categories,
  search,
  status,
  category,
  sort,
  publicWebsiteUrl,
  basePath,
  readOnly = false,
}: {
  kind: "posts" | "pages";
  data: Paginated<ContentSummary>;
  categories: Category[];
  search: string;
  status: string;
  category: string;
  sort: string;
  publicWebsiteUrl?: string;
  basePath?: string;
  readOnly?: boolean;
}) {
  const router = useRouter();
  const selectAllRef = useRef<HTMLInputElement>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkMessage, setBulkMessage] = useState("");

  const isPosts = kind === "posts";
  const routeBase = basePath || `/admin/${kind}`;
  const isStudioV2 = routeBase.startsWith("/studio-v2");
  const label = isPosts ? "Blog Studio" : "Pages";
  const stats = data.stats || { total: data.total, published: 0, drafts: 0, scheduled: 0, trashed: 0, total_views: 0 };
  const query = new URLSearchParams({ search, status, sort });
  if (category) query.set("category", category);
  const pageHref = (page: number) => `?${new URLSearchParams({ ...Object.fromEntries(query), page: String(page) })}`;

  const selectableItems = useMemo(
    () => isPosts && !readOnly ? data.items.filter(item => item.status !== "trash") : [],
    [data.items, isPosts, readOnly],
  );
  const selectableIds = useMemo(() => selectableItems.map(item => item.id), [selectableItems]);
  const allVisibleSelected = selectableIds.length > 0 && selectableIds.every(id => selectedIds.has(id));
  const someVisibleSelected = selectableIds.some(id => selectedIds.has(id));

  useEffect(() => {
    setSelectedIds(new Set());
    setBulkMessage("");
  }, [data.page, search, status, category, sort]);

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = someVisibleSelected && !allVisibleSelected;
    }
  }, [someVisibleSelected, allVisibleSelected]);

  function toggleOne(id: number, checked: boolean) {
    setBulkMessage("");
    setSelectedIds(current => {
      const next = new Set(current);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  function toggleAll(checked: boolean) {
    setBulkMessage("");
    setSelectedIds(current => {
      const next = new Set(current);
      for (const id of selectableIds) {
        if (checked) next.add(id);
        else next.delete(id);
      }
      return next;
    });
  }

  async function deleteSelected() {
    if (bulkBusy || selectedIds.size === 0 || !isPosts || readOnly) return;

    const selectedItems = data.items.filter(item => selectedIds.has(item.id));
    const publishedCount = selectedItems.filter(item => item.status === "published").length;
    const draftCount = selectedItems.filter(item => item.status === "draft").length;
    const scheduledCount = selectedItems.filter(item => item.status === "scheduled").length;
    const statusSummary = [
      publishedCount ? `${publishedCount} published` : "",
      draftCount ? `${draftCount} draft` : "",
      scheduledCount ? `${scheduledCount} scheduled` : "",
    ].filter(Boolean).join(", ");
    const warning = publishedCount
      ? "\n\nWarning: published posts are included and will disappear from the public site."
      : "";
    const confirmed = window.confirm(
      `Delete ${selectedItems.length} selected post${selectedItems.length === 1 ? "" : "s"}?\n\n` +
      `This safely moves them to Trash${statusSummary ? ` (${statusSummary})` : ""}.` +
      warning,
    );
    if (!confirmed) return;

    setBulkBusy(true);
    setBulkMessage("");
    const deleted = new Set<number>();
    try {
      const csrfResponse = await fetch("/api/admin/auth/csrf", { cache: "no-store" });
      if (!csrfResponse.ok) throw new Error("csrf");
      const csrf = await csrfResponse.json() as { csrfToken?: string };
      if (!csrf.csrfToken) throw new Error("csrf");

      for (const item of selectedItems) {
        const response = await fetch(`/api/admin/content/posts/${item.id}/trash`, {
          method: "POST",
          headers: { "X-CSRF-Token": csrf.csrfToken },
        });
        if (response.ok) deleted.add(item.id);
      }

      if (deleted.size === selectedItems.length) {
        setBulkMessage(`${deleted.size} post${deleted.size === 1 ? "" : "s"} moved to Trash.`);
      } else if (deleted.size > 0) {
        setBulkMessage(`${deleted.size} of ${selectedItems.length} posts moved to Trash. Retry the remaining selection.`);
      } else {
        setBulkMessage("Selected posts could not be deleted. Nothing was changed.");
      }

      if (deleted.size > 0) {
        setSelectedIds(current => {
          const next = new Set(current);
          deleted.forEach(id => next.delete(id));
          return next;
        });
        router.refresh();
      }
    } catch {
      setBulkMessage("Content service is temporarily unavailable. Nothing was deleted.");
    } finally {
      setBulkBusy(false);
    }
  }

  return <>
    <section className="page-heading studio-heading">
      <div><span className="eyebrow">CONTENT WORKSPACE</span><h1>{label}</h1><p>{isPosts ? "Create, optimize and publish your market coverage from one focused workspace." : "Manage the site’s evergreen public pages."}</p></div>
      <div className="studio-heading-actions">
        {isPosts && (
          <Link
            className="secondary-button studio-ai-button"
            href={isStudioV2 ? "/studio-v2/ai" : "/admin/posts/ai-writer"}
          >
            <span aria-hidden="true">✦</span>
            Generate with AI
          </Link>
        )}

        <Link
          className="primary-button button-with-icon"
          href={isStudioV2 ? "/studio-v2?new=1" : `/admin/${kind}/new`}
        >
          <span aria-hidden="true">＋</span>
          New {isPosts ? "Post" : "Page"}
        </Link>
      </div>
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
      <div className="content-panel-head">
        <div><h2>{isPosts ? "All posts" : "All pages"}</h2><p>{number(data.total)} result{data.total === 1 ? "" : "s"} in the current view</p></div>
        {isPosts && !readOnly && selectedIds.size > 0 && <div className="studio-heading-actions" role="status" aria-live="polite">
          <strong>{selectedIds.size} selected</strong>
          <button className="secondary-button" type="button" disabled={bulkBusy} onClick={() => setSelectedIds(new Set())}>Clear selection</button>
          <button className="primary-button" type="button" disabled={bulkBusy} onClick={deleteSelected}>{bulkBusy ? "Deleting…" : "Delete selected"}</button>
        </div>}
      </div>
      {bulkMessage && <p className="action-error" role="status">{bulkMessage}</p>}
      <form className="filter-bar studio-filters" method="get">
        <label className="search-field"><span className="sr-only">Search</span><span aria-hidden="true">⌕</span><input name="search" defaultValue={search} placeholder={`Search ${isPosts ? "title, slug or keyword" : "pages"}`} /></label>
        <label><span className="sr-only">Status</span><select name="status" defaultValue={status}><option value="all">All statuses</option><option value="published">Published</option><option value="draft">Drafts</option>{isPosts && <><option value="scheduled">Scheduled</option><option value="trash">Trashed</option></>}</select></label>
        <label><span className="sr-only">Category</span><select name="category" defaultValue={category}><option value="">All categories</option>{categories.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
        <label><span className="sr-only">Sort</span><select name="sort" defaultValue={sort}><option value="updated_desc">Recently updated</option><option value="updated_asc">Oldest updated</option><option value="title_asc">Title A–Z</option><option value="title_desc">Title Z–A</option><option value="published_desc">Recently published</option></select></label>
        <button className="secondary-button">Apply filters</button>
        {(search || status !== "all" || category || sort !== "updated_desc") && <Link className="clear-filter" href={routeBase}>Clear</Link>}
      </form>
      {data.items.length ? <div className="table-wrap"><table className="cms-table studio-table">
        <thead><tr><th><input ref={selectAllRef} type="checkbox" disabled={!isPosts || readOnly || selectableIds.length === 0} checked={allVisibleSelected} onChange={event => toggleAll(event.target.checked)} aria-label="Select all visible posts" /></th><th>Post</th><th>ID</th><th>Category</th><th>Status</th><th>Views</th><th>SEO</th><th>Slug</th><th>Author</th><th>Updated</th><th>Actions</th></tr></thead>
        <tbody>{data.items.map(item => {
          const previewUrl = publicWebsiteUrl && item.status === "published" ? `${publicWebsiteUrl}/${isPosts ? "blog" : "page"}/${encodeURIComponent(item.slug)}` : undefined;
          const seoChecked = Boolean(item.seo_checked);
          const seoScore = seoChecked && typeof item.seo_score === "number" ? item.seo_score : null;
          const seoIssues = Array.isArray(item.seo_issues) ? item.seo_issues : [];
          const selectable = isPosts && !readOnly && item.status !== "trash";
          return <tr key={item.id}>
            <td><input type="checkbox" aria-label={`Select ${item.title}`} disabled={!selectable || bulkBusy} checked={selectedIds.has(item.id)} onChange={event => toggleOne(item.id, event.target.checked)} /></td>
            <td className="post-cell"><Link
              className="post-thumbnail"
              href={
                isStudioV2
                  ? `/studio-v2?post_id=${item.id}`
                  : `/admin/${kind}/${item.id}/edit`
              } aria-label={`Edit ${item.title}`} style={item.featured_image ? { backgroundImage: `url(${item.featured_image})` } : undefined}>{!item.featured_image && <span aria-hidden="true">VR</span>}</Link><div><Link
                className="post-title"
                href={
                  isStudioV2
                    ? `/studio-v2?post_id=${item.id}`
                    : `/admin/${kind}/${item.id}/edit`
                }
              >
                {item.title}
              </Link><small>{item.scheduled_at && item.status === "scheduled" ? `Scheduled ${shortDate(item.scheduled_at)}` : item.content_type.replace("_", " ")}</small></div></td>
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
            <td><ContentActions
              kind={kind}
              id={item.id}
              status={item.status}
              previewUrl={previewUrl}
              previewLabel="Open preview"
              compact
              readOnly={readOnly}
              editHref={
                isStudioV2
                  ? `/studio-v2?post_id=${item.id}`
                  : undefined
              }
            /></td>
          </tr>})}</tbody>
      </table></div> : <section className="state-panel empty-table"><strong>No {isPosts ? "posts" : "pages"} found</strong><p>Create a draft or change the current filters.</p></section>}
      <nav className="pagination" aria-label="Pagination"><span>Page {data.page} of {data.pages}</span><div>{data.page > 1 ? <Link href={pageHref(data.page - 1)}>← Previous</Link> : <span aria-disabled="true">← Previous</span>}{data.page < data.pages ? <Link href={pageHref(data.page + 1)}>Next →</Link> : <span aria-disabled="true">Next →</span>}</div></nav>
    </section>
  </>;
}
