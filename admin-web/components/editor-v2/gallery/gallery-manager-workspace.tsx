"use client";

import { useEffect, useState } from "react";

type MediaAsset = {
  id: number;
  public_url: string;
  thumbnail_url?: string | null;
  original_filename: string;
  alt_text?: string;
};

type SavedGallery = {
  id: string;
  title: string;
  slug: string;
  mediaIds: number[];
  columns: 2 | 3 | 4 | 5;
  updatedAt: string;
};

const STORAGE_KEY = "venusrealm-custom-cms-v2-galleries";

function slugify(value: string): string {
  return value.toLowerCase().trim().replace(/[^a-z0-9\s-]/g, "").replace(/\s+/g, "-").replace(/-+/g, "-");
}

export function GalleryManagerWorkspace() {
  const [media, setMedia] = useState<MediaAsset[]>([]);
  const [galleries, setGalleries] = useState<SavedGallery[]>([]);
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [selected, setSelected] = useState<number[]>([]);
  const [columns, setColumns] = useState<2 | 3 | 4 | 5>(3);
  const [message, setMessage] = useState("");

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved) setGalleries(JSON.parse(saved) as SavedGallery[]);
    } catch {
      setMessage("Saved galleries could not be restored.");
    }

    void fetch("/api/admin/media?page=1&page_size=100&state=active", { cache: "no-store", credentials: "same-origin" })
      .then(async response => {
        const payload = (await response.json()) as { items?: MediaAsset[] };
        if (response.ok) setMedia(payload.items || []);
      })
      .catch(() => setMessage("Media Library could not be loaded."));
  }, []);

  function persist(next: SavedGallery[]) {
    setGalleries(next);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }

  function saveGallery() {
    if (!title.trim()) { setMessage("Gallery title is required."); return; }
    if (!selected.length) { setMessage("Select at least one image."); return; }
    const gallery: SavedGallery = {
      id: crypto.randomUUID(), title: title.trim(), slug: slugify(slug || title),
      mediaIds: selected, columns, updatedAt: new Date().toISOString(),
    };
    persist([gallery, ...galleries]);
    setTitle(""); setSlug(""); setSelected([]); setColumns(3); setMessage("Gallery saved locally.");
  }

  function removeGallery(id: string) {
    if (!window.confirm("Delete this saved gallery?")) return;
    persist(galleries.filter(item => item.id !== id));
    setMessage("Gallery deleted.");
  }

  return (
    <section className="studio-gallery-workspace">
      <div className="studio-gallery-builder">
        <div className="studio-gallery-fields">
          <label><span>Gallery title</span><input value={title} onChange={event => { const value = event.target.value; setTitle(value); if (!slug) setSlug(slugify(value)); }} placeholder="Homepage market gallery" /></label>
          <label><span>Slug</span><input value={slug} onChange={event => setSlug(slugify(event.target.value))} placeholder="homepage-market-gallery" /></label>
          <label><span>Columns</span><select value={columns} onChange={event => setColumns(Number(event.target.value) as 2 | 3 | 4 | 5)}><option value={2}>2 columns</option><option value={3}>3 columns</option><option value={4}>4 columns</option><option value={5}>5 columns</option></select></label>
          <button type="button" className="primary-button" onClick={saveGallery}>Save gallery</button>
        </div>
        {message ? <div className="studio-media-message" role="status">{message}</div> : null}
        {media.length ? (
          <div className="studio-gallery-media-grid">
            {media.map(item => {
              const active = selected.includes(item.id);
              return (
                <button type="button" key={item.id} className={active ? "selected" : ""} onClick={() => setSelected(current => active ? current.filter(id => id !== item.id) : [...current, item.id])}>
                  <img
                    src={item.thumbnail_url || item.public_url}
                    alt={item.alt_text || ""}
                    loading="lazy"
                    decoding="async"
                    onError={event => {
                      if (event.currentTarget.dataset.fallbackApplied) return;
                      event.currentTarget.dataset.fallbackApplied = "true";
                      event.currentTarget.src = "/media-fallback.svg";
                    }}
                  />
                  <span>{active ? "Selected" : item.original_filename}</span>
                </button>
              );
            })}
          </div>
        ) : <div className="studio-media-empty"><strong>No active media found</strong><span>Upload images in Media Library first.</span></div>}
      </div>
      <aside className="studio-gallery-saved">
        <h2>Saved galleries</h2>
        {galleries.length ? galleries.map(gallery => (
          <article key={gallery.id}><div><strong>{gallery.title}</strong><small>{gallery.mediaIds.length} images · {gallery.columns} columns</small><code>/{gallery.slug}</code></div><button type="button" className="danger-link" onClick={() => removeGallery(gallery.id)}>Delete</button></article>
        )) : <p>No saved galleries yet.</p>}
      </aside>
    </section>
  );
}
