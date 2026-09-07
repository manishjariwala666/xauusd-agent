"use client";
/* eslint-disable @next/next/no-img-element -- local/staging thumbnail hosts are selected server-side */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { MediaAsset } from "@/lib/media-api";

type Selection = { id: number | null; url: string | null; alt: string };
const csrf = async () => fetch("/api/admin/auth/csrf", { cache: "no-store" }).then(r => r.json()) as Promise<{ csrfToken: string }>;

function mediaPreviewUrl(value: string | null | undefined) {
  const clean = String(value || "").trim();
  if (!clean) return null;

  if (/^(blob:|data:)/i.test(clean)) return clean;

  if (/^https?:\/\//i.test(clean)) {
    try {
      const parsed = new URL(clean);

      if (
        parsed.hostname === "127.0.0.1" ||
        parsed.hostname === "localhost"
      ) {
        const localPath = `${parsed.pathname}${parsed.search}`;
        return `/api/admin/media-preview/${localPath.replace(/^\/+/, "")}`;
      }

      return clean;
    } catch {
      return null;
    }
  }

  return `/api/admin/media-preview/${clean.replace(/^\/+/, "")}`;
}

export function FeaturedImagePicker(props: {
  contentId?: number;
  initial: Selection;
  onPendingChange?: (mediaId: number | null) => void;
  onSelectionChange?: (selection: Selection) => void;
}) {
  const { initial } = props;
  return <FeaturedImagePickerForm key={`${initial.id || ""}:${initial.url || ""}:${initial.alt}`} {...props} />;
}

function FeaturedImagePickerForm({ contentId, initial, onPendingChange, onSelectionChange }: {
  contentId?: number;
  initial: Selection;
  onPendingChange?: (mediaId: number | null) => void;
  onSelectionChange?: (selection: Selection) => void;
}) {
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
  const [uploadPreview, setUploadPreview] = useState<string | null>(null);
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    return () => {
      if (uploadPreview) URL.revokeObjectURL(uploadPreview);
    };
  }, [uploadPreview]);

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
    const nextSelection = { id: item.id, url: item.public_url, alt: item.alt_text };
    setCurrent(nextSelection);
    onSelectionChange?.(nextSelection);
    setOpen(false);
    setMessage(contentId ? "Featured image saved." : "Image selected. Save the content to persist it.");
  }
  async function remove() {
    if (contentId) {
      setBusy(true);
      try { const token = await csrf(); const response = await fetch(`/api/admin/featured-image/${contentId}`, { method: "DELETE", headers: { "X-CSRF-Token": token.csrfToken } }); if (!response.ok) { setMessage("Featured image could not be removed."); return; } router.refresh(); }
      finally { setBusy(false); }
    } else onPendingChange?.(null);
    const nextSelection = { id: null, url: null, alt: "" };
    setCurrent(nextSelection);
    onSelectionChange?.(nextSelection);
    setMessage("Featured image removed.");
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
    try { const token = await csrf(); const response = await fetch(`/api/admin/media/${current.id}`, { method: "PATCH", headers: { "Content-Type": "application/json", "X-CSRF-Token": token.csrfToken }, body: JSON.stringify({ alt_text: current.alt }) }); const item = await response.json() as MediaAsset & { detail?: string }; if (!response.ok) { setMessage(item.detail || "Alt text could not be saved."); return; } setCurrent(value => {
      const nextSelection = { ...value, alt: item.alt_text };
      onSelectionChange?.(nextSelection);
      return nextSelection;
    }); setMessage("Alt text saved."); }
    finally { setBusy(false); }
  }
  return <section className="editor-card featured-card"><div className="card-heading"><div><h2>Featured image</h2><p>Media Library</p></div></div>
    {current.url ? <><div className="featured-placeholder selected">
  {!imageFailed ? (
    <img
      src={mediaPreviewUrl(current.url) || ""}
      alt={current.alt || "Featured image preview"}
      onLoad={() => setImageFailed(false)}
      onError={() => setImageFailed(true)}
    />
  ) : (
    <div className="featured-image-error">
      <b>Image preview unavailable</b>
      <small>The saved file URL is broken or inaccessible. Replace the image from Media Library.</small>
    </div>
  )}
</div><div className="featured-controls"><button type="button" className="secondary-button" onClick={showPicker} disabled={busy}>Replace</button><button type="button" className="text-button danger-link" onClick={remove} disabled={busy}>Remove</button></div>{current.id && <div className="featured-alt-form"><label>Alt text<input value={current.alt} onChange={event => setCurrent(value => ({ ...value, alt: event.target.value }))} maxLength={500} placeholder="Describe this image" /></label><button type="button" className="secondary-button" onClick={updateAlt} disabled={busy}>Save alt text</button></div>}</> : <div className="featured-placeholder"><b>▧</b><span>No featured image</span><small>Choose an existing image or upload a new one.</small></div>}
    {!current.url && <div className="featured-controls"><button type="button" className="secondary-button" onClick={showPicker} disabled={busy}>Choose from library</button><button type="button" className="text-button" onClick={() => setUploading(value => !value)}>Upload new</button></div>}
    {uploading && <div className="featured-upload">
      <label>Image<input type="file" accept="image/jpeg,image/png,image/webp,image/gif" onChange={event => {
        const file = event.target.files?.[0] || null;
        setUploadFile(file);
        setUploadPreview(file ? URL.createObjectURL(file) : null);
      }} /></label>
      {uploadPreview && <div className="featured-upload-preview"><img src={uploadPreview} alt={uploadAlt || "Selected image preview"} /><small>Preview before WebP optimisation</small></div>}
      <label>Alt text<input value={uploadAlt} onChange={event => setUploadAlt(event.target.value)} maxLength={500} /></label>
      <button type="button" className="primary-button" onClick={upload} disabled={busy || !uploadFile}>{busy ? "Optimising…" : "Upload and select"}</button>
    </div>}
    {message && <small className="picker-message" role="status">{message}</small>}
    {open && <div className="media-picker"><div className="picker-search"><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search media" aria-label="Search media" /><button type="button" className="secondary-button" onClick={() => loadMedia(search)}>Search</button></div>{busy ? <p>Loading media…</p> : items.length ? <div className="picker-grid">{items.map(item => <button type="button" onClick={() => select(item)} key={item.id}><img
  src={mediaPreviewUrl(item.thumbnail_url || item.public_url) || ""}
  alt=""
  loading="lazy"
  decoding="async"
/><small>{item.original_filename}</small></button>)}</div> : <p>No media found. Upload a new image instead.</p>}<button type="button" className="text-button" onClick={() => setOpen(false)}>Close library</button></div>}
  </section>;
}
