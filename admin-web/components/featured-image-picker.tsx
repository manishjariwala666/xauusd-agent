"use client";
/* eslint-disable @next/next/no-img-element -- local/staging thumbnail hosts are selected server-side */

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { MediaAsset } from "@/lib/media-api";

type Selection = { id: number | null; url: string | null; alt: string };
const csrf = async () => fetch("/api/admin/auth/csrf", { cache: "no-store" }).then(r => r.json()) as Promise<{ csrfToken: string }>;

export function FeaturedImagePicker({ contentId, initial, onPendingChange }: { contentId?: number; initial: Selection; onPendingChange?: (mediaId: number | null) => void }) {
  const router = useRouter();
  const [current, setCurrent] = useState(initial);
  const [items, setItems] = useState<MediaAsset[]>([]);
  const [open, setOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [search, setSearch] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadAlt, setUploadAlt] = useState("");

  async function loadMedia(term = "") {
    setBusy(true); setMessage("");
    try {
      const response = await fetch(`/api/admin/media?page_size=12&state=active&search=${encodeURIComponent(term)}`, { cache: "no-store" });
      const result = await response.json() as { items?: MediaAsset[]; message?: string };
      if (!response.ok) { setMessage(result.message || "Media could not be loaded."); return; }
      setItems(result.items || []);
    } catch { setMessage("Media service is temporarily unavailable."); } finally { setBusy(false); }
  }
  async function showPicker() { setOpen(true); await loadMedia(); }
  async function select(item: MediaAsset) {
    if (contentId) {
      setBusy(true);
      try {
        const token = await csrf();
        const response = await fetch(`/api/admin/featured-image/${contentId}`, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": token.csrfToken }, body: JSON.stringify({ media_id: item.id }) });
        if (!response.ok) { const error = await response.json() as { detail?: string }; setMessage(error.detail || "Featured image could not be saved."); return; }
        router.refresh();
      } finally { setBusy(false); }
    } else onPendingChange?.(item.id);
    setCurrent({ id: item.id, url: item.public_url, alt: item.alt_text }); setOpen(false); setMessage(contentId ? "Featured image saved." : "Image selected. Save the content to persist it.");
  }
  async function remove() {
    if (contentId) {
      setBusy(true);
      try { const token = await csrf(); const response = await fetch(`/api/admin/featured-image/${contentId}`, { method: "DELETE", headers: { "X-CSRF-Token": token.csrfToken } }); if (!response.ok) { setMessage("Featured image could not be removed."); return; } router.refresh(); }
      finally { setBusy(false); }
    } else onPendingChange?.(null);
    setCurrent({ id: null, url: null, alt: "" }); setMessage("Featured image removed.");
  }
  async function upload() {
    if (!uploadFile) { setMessage("Choose an image to upload."); return; }
    setBusy(true); setMessage("");
    try {
      const form = new FormData(); form.set("file", uploadFile); form.set("alt_text", uploadAlt); form.set("caption", "");
      const token = await csrf(); const response = await fetch("/api/admin/media/upload", { method: "POST", headers: { "X-CSRF-Token": token.csrfToken }, body: form });
      const result = await response.json() as MediaAsset & { detail?: string };
      if (!response.ok) { setMessage(result.detail || "Upload failed."); return; }
      await select(result);
    } catch { setMessage("Media service is temporarily unavailable."); } finally { setBusy(false); }
  }
  async function updateAlt() {
    if (!current.id) return; setBusy(true);
    try { const token = await csrf(); const response = await fetch(`/api/admin/media/${current.id}`, { method: "PATCH", headers: { "Content-Type": "application/json", "X-CSRF-Token": token.csrfToken }, body: JSON.stringify({ alt_text: current.alt }) }); const item = await response.json() as MediaAsset & { detail?: string }; if (!response.ok) { setMessage(item.detail || "Alt text could not be saved."); return; } setCurrent(value => ({ ...value, alt: item.alt_text })); setMessage("Alt text saved."); }
    finally { setBusy(false); }
  }
  return <section className="editor-card featured-card"><div className="card-heading"><div><h2>Featured image</h2><p>Media Library</p></div></div>
    {current.url ? <><div className="featured-placeholder selected" role="img" aria-label={current.alt || "Featured image preview"} style={{ backgroundImage: `url(${current.url})` }} /><div className="featured-controls"><button type="button" className="secondary-button" onClick={showPicker} disabled={busy}>Replace</button><button type="button" className="text-button danger-link" onClick={remove} disabled={busy}>Remove</button></div>{current.id && <div className="featured-alt-form"><label>Alt text<input value={current.alt} onChange={event => setCurrent(value => ({ ...value, alt: event.target.value }))} maxLength={500} placeholder="Describe this image" /></label><button type="button" className="secondary-button" onClick={updateAlt} disabled={busy}>Save alt text</button></div>}</> : <div className="featured-placeholder"><b>▧</b><span>No featured image</span><small>Choose an existing image or upload a new one.</small></div>}
    {!current.url && <div className="featured-controls"><button type="button" className="secondary-button" onClick={showPicker} disabled={busy}>Choose from library</button><button type="button" className="text-button" onClick={() => setUploading(value => !value)}>Upload new</button></div>}
    {uploading && <div className="featured-upload"><label>Image<input type="file" accept="image/jpeg,image/png,image/webp,image/gif" onChange={event => setUploadFile(event.target.files?.[0] || null)} /></label><label>Alt text<input value={uploadAlt} onChange={event => setUploadAlt(event.target.value)} maxLength={500} /></label><button type="button" className="primary-button" onClick={upload} disabled={busy || !uploadFile}>{busy ? "Validating…" : "Upload and select"}</button></div>}
    {message && <small className="picker-message" role="status">{message}</small>}
    {open && <div className="media-picker"><div className="picker-search"><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search media" aria-label="Search media" /><button type="button" className="secondary-button" onClick={() => loadMedia(search)}>Search</button></div>{busy ? <p>Loading media…</p> : items.length ? <div className="picker-grid">{items.map(item => <button type="button" onClick={() => select(item)} key={item.id}><img src={item.thumbnail_url || item.public_url} alt="" loading="lazy" decoding="async" /><small>{item.original_filename}</small></button>)}</div> : <p>No media found. Upload a new image instead.</p>}<button type="button" className="text-button" onClick={() => setOpen(false)}>Close library</button></div>}
  </section>;
}
