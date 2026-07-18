"use client";
/* eslint-disable @next/next/no-img-element -- server-generated thumbnails may use local or staging adapters */

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import type { Paginated } from "@/lib/content-api";
import type { MediaAsset } from "@/lib/media-api";

const formatSize = (bytes: number) => bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
const formatDate = (value: string) => new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(new Date(value));
const csrf = async () => fetch("/api/admin/auth/csrf", { cache: "no-store" }).then(r => r.json()) as Promise<{ csrfToken: string }>;

export function MediaLibrary({ data, filters, selectFor }: { data: Paginated<MediaAsset>; filters: Record<string, string>; selectFor?: number }) {
  const router = useRouter();
  const [view, setView] = useState<"grid" | "list">("grid");
  const [showUpload, setShowUpload] = useState(false);
  const [editing, setEditing] = useState<MediaAsset | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const pageHref = (page: number) => `?${new URLSearchParams({ ...filters, page: String(page), ...(selectFor ? { selectFor: String(selectFor) } : {}) })}`;

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return; setBusy(true); setMessage("");
    try {
      const token = await csrf();
      const response = await fetch("/api/admin/media/upload", { method: "POST", headers: { "X-CSRF-Token": token.csrfToken }, body: new FormData(event.currentTarget) });
      const result = await response.json() as { detail?: string; message?: string };
      if (!response.ok) { setMessage(result.detail || result.message || "Upload failed."); return; }
      setShowUpload(false); setMessage("Image uploaded safely."); router.refresh();
    } catch { setMessage("Media service is temporarily unavailable."); } finally { setBusy(false); }
  }
  async function mutation(path: string, method: "POST" | "PATCH" | "DELETE", body?: object) {
    if (busy) return; setBusy(true); setMessage("");
    try {
      const token = await csrf();
      const response = await fetch(path, { method, headers: { "X-CSRF-Token": token.csrfToken, ...(body ? { "Content-Type": "application/json" } : {}) }, body: body ? JSON.stringify(body) : undefined });
      const result = await response.json() as { detail?: string; message?: string };
      if (!response.ok) { setMessage(result.detail || result.message || "Action failed."); return; }
      setEditing(null); router.refresh();
    } catch { setMessage("Media service is temporarily unavailable."); } finally { setBusy(false); }
  }
  async function saveMetadata(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!editing) return;
    const form = new FormData(event.currentTarget);
    await mutation(`/api/admin/media/${editing.id}`, "PATCH", { alt_text: form.get("alt_text"), caption: form.get("caption") });
  }
  async function copyUrl(url: string) {
    try { await navigator.clipboard.writeText(url); setMessage("Public URL copied."); } catch { setMessage("Copy was blocked by the browser. Open the image and copy its URL."); }
  }
  return <>
    <section className="page-heading studio-heading"><div><span className="eyebrow">CONTENT ASSETS</span><h1>Media Library</h1><p>Upload, describe and safely reuse images across posts and pages.</p></div><button className="primary-button" onClick={() => setShowUpload(value => !value)}>＋ Upload Media</button></section>
    {message && <div className={message.includes("failed") || message.includes("unavailable") ? "form-error media-message" : "media-message success"} role="status">{message}</div>}
    {showUpload && <form className="media-upload-card" onSubmit={upload}><div><h2>Upload image</h2><p>JPEG, PNG, WebP or GIF. Maximum 8 MB. Files are decoded and validated.</p></div><label>Image file<input name="file" type="file" accept="image/jpeg,image/png,image/webp,image/gif" required /></label><label>Alt text<input name="alt_text" maxLength={500} placeholder="Describe the image for accessibility" /></label><label>Caption<textarea name="caption" rows={2} maxLength={2000} /></label><div><button className="primary-button" disabled={busy}>{busy ? "Validating…" : "Upload image"}</button><button type="button" className="text-button" onClick={() => setShowUpload(false)}>Cancel</button></div></form>}
    <section className="content-panel media-panel">
      <div className="media-toolbar"><form className="filter-bar media-filters" method="get"><label className="search-field"><span aria-hidden="true">⌕</span><input name="search" defaultValue={filters.search} placeholder="Search filename, alt text or caption" aria-label="Search media" /></label><select name="source" defaultValue={filters.source} aria-label="Source"><option value="all">All sources</option><option value="manual_upload">Manual uploads</option><option value="local_import">Local imports</option><option value="ai_generated">AI generated</option></select><select name="date_filter" defaultValue={filters.date_filter} aria-label="Upload date"><option value="all">Any date</option><option value="7d">Last 7 days</option><option value="30d">Last 30 days</option><option value="90d">Last 90 days</option></select><select name="state" defaultValue={filters.state} aria-label="Media state"><option value="active">Active</option><option value="trash">Trash</option><option value="all">All</option></select>{selectFor && <input type="hidden" name="selectFor" value={selectFor} />}<button className="secondary-button">Filter</button></form><div className="view-toggle" aria-label="View style"><button className={view === "grid" ? "active" : ""} onClick={() => setView("grid")} aria-pressed={view === "grid"}>Grid</button><button className={view === "list" ? "active" : ""} onClick={() => setView("list")} aria-pressed={view === "list"}>List</button></div></div>
      {data.items.length ? <div className={`media-collection ${view}`}>{data.items.map(item => <article className="media-item" key={item.id}>
        <a className="media-thumb" href={item.public_url} target="_blank" rel="noreferrer" aria-label={`View ${item.original_filename}`}><img src={item.thumbnail_url || item.public_url} alt="" loading="lazy" decoding="async" /></a>
        <div className="media-info"><strong title={item.original_filename}>{item.original_filename}</strong><span>{item.width} × {item.height} · {formatSize(item.size_bytes)}</span><span>{item.mime_type} · {formatDate(item.created_at)}</span><span className={item.alt_text ? "alt-ok" : "alt-missing"}>{item.alt_text ? "Alt text added" : "Missing alt text"}</span><span>{item.source_type.replaceAll("_", " ").toLowerCase()} · Used {item.usage_count}×</span></div>
        <div className="media-actions"><a href={item.public_url} target="_blank" rel="noreferrer">View</a><button onClick={() => setEditing(item)}>Edit</button><button onClick={() => copyUrl(item.public_url)}>Copy URL</button>{selectFor && !item.deleted_at && <button onClick={() => mutation(`/api/admin/featured-image/${selectFor}`, "POST", { media_id: item.id })}>Set featured</button>}{item.deleted_at ? <><button onClick={() => mutation(`/api/admin/media/${item.id}/restore`, "POST")}>Restore</button><button className="danger-link" onClick={() => window.confirm("Permanently delete this trashed image? This cannot be undone.") && mutation(`/api/admin/media/${item.id}?confirmed=true`, "DELETE")}>Delete permanently</button></> : <button className="danger-link" onClick={() => window.confirm("Move this media item to trash?") && mutation(`/api/admin/media/${item.id}/trash`, "POST")}>Trash</button>}</div>
      </article>)}</div> : <section className="state-panel empty-table"><strong>No media found</strong><p>Upload an approved image or change the current filters.</p></section>}
      <nav className="pagination" aria-label="Media pagination"><span>Page {data.page} of {data.pages} · {data.total} items</span><div>{data.page > 1 ? <Link href={pageHref(data.page - 1)}>← Previous</Link> : <span aria-disabled="true">← Previous</span>}{data.page < data.pages ? <Link href={pageHref(data.page + 1)}>Next →</Link> : <span aria-disabled="true">Next →</span>}</div></nav>
    </section>
    {editing && <div className="media-dialog-backdrop" role="presentation" onMouseDown={() => setEditing(null)}><section className="media-dialog" role="dialog" aria-modal="true" aria-labelledby="media-edit-title" onMouseDown={event => event.stopPropagation()}><h2 id="media-edit-title">Edit image metadata</h2><div className="media-detail-preview" style={{ backgroundImage: `url(${editing.thumbnail_url || editing.public_url})` }} /><dl><div><dt>Filename</dt><dd>{editing.original_filename}</dd></div><div><dt>Dimensions</dt><dd>{editing.width} × {editing.height}</dd></div><div><dt>Size / type</dt><dd>{formatSize(editing.size_bytes)} · {editing.mime_type}</dd></div><div><dt>Uploaded</dt><dd>{formatDate(editing.created_at)}</dd></div><div><dt>Source</dt><dd>{editing.source_type}</dd></div></dl><form onSubmit={saveMetadata}><label>Alt text<input name="alt_text" defaultValue={editing.alt_text} maxLength={500} /></label><label>Caption<textarea name="caption" defaultValue={editing.caption} rows={3} maxLength={2000} /></label><div><button className="primary-button" disabled={busy}>Save metadata</button><button className="text-button" type="button" onClick={() => setEditing(null)}>Cancel</button></div></form></section></div>}
  </>;
}
