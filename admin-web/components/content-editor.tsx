"use client";

import { FormEvent, useEffect, useMemo, useState, type CSSProperties } from "react";
import { useRouter } from "next/navigation";
import type { Category, ContentDetail } from "@/lib/content-api";
import { FeaturedImagePicker } from "./featured-image-picker";
import { SeoWorkbench } from "./seo-workbench";
import type { SeoDetail } from "@/lib/seo-api";

type Intent = "save" | "draft" | "publish" | "schedule";
const dateTime = (value?: string | null) => value ? new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "Not set";

export function ContentEditor({ kind, initial, seo, categories, publicWebsiteUrl }: {
  kind: "posts" | "pages"; initial?: ContentDetail | null; seo?: SeoDetail | null; categories: Category[]; publicWebsiteUrl?: string;
}) {
  const router = useRouter();
  const [title, setTitle] = useState(initial?.title || "");
  const [slug, setSlug] = useState(initial?.slug || "");
  const [excerpt, setExcerpt] = useState(initial?.excerpt || "");
  const [body, setBody] = useState(initial?.body || "");
  const [scheduledAt, setScheduledAt] = useState(initial?.scheduled_at ? initial.scheduled_at.slice(0, 16) : "");
  const [pendingMediaId, setPendingMediaId] = useState<number | null>(initial?.featured_media_id || null);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [savedMessage, setSavedMessage] = useState(initial ? "All changes saved" : "New unsaved content");
  const words = useMemo(() => body.trim() ? body.replace(/<[^>]+>/g, " ").trim().split(/\s+/).length : 0, [body]);
  const minutes = Math.max(1, Math.ceil(words / 220));
  const publicUrl = publicWebsiteUrl && slug ? `${publicWebsiteUrl}/${kind === "posts" ? "blog" : "page"}/${encodeURIComponent(slug)}` : "Public URL is not configured locally";
  const isPublished = initial?.status === "published";
  const isTrashed = initial?.status === "trash";
  const displayStatus = !isPublished && !isTrashed && initial?.scheduled_at && new Date(initial.scheduled_at) > new Date() ? "scheduled" : initial?.status || "draft";
  const canSchedule = Boolean(scheduledAt) && new Date(scheduledAt) > new Date();
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (dirty) event.preventDefault(); };
    addEventListener("beforeunload", warn); return () => removeEventListener("beforeunload", warn);
  }, [dirty]);

  async function csrf() { return fetch("/api/admin/auth/csrf", { cache: "no-store" }).then(r => r.json()) as Promise<{ csrfToken: string }>; }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy || isTrashed) return;
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    const intent = (submitter?.value || "save") as Intent;
    setBusy(true); setMessage(""); setSavedMessage("Saving…");
    const data = new FormData(event.currentTarget);
    const payload = Object.fromEntries(data.entries());
    payload.body = body; payload.title = title; payload.slug = slug; payload.excerpt = excerpt;
    payload.status = intent === "publish" ? "published" : intent === "draft" || intent === "schedule" ? "draft" : String(payload.status || "draft");
    payload.category_id = payload.category_id ? Number(payload.category_id) as never : null as never;
    payload.scheduled_at = intent === "schedule" && payload.scheduled_at ? new Date(String(payload.scheduled_at)).toISOString() as never : intent === "schedule" ? null as never : payload.scheduled_at ? new Date(String(payload.scheduled_at)).toISOString() as never : null as never;
    try {
      const token = await csrf();
      const endpoint = initial ? `/api/admin/content/${kind}/${initial.id}` : `/api/admin/content/${kind}`;
      const response = await fetch(endpoint, { method: initial ? "PATCH" : "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": token.csrfToken }, body: JSON.stringify(payload) });
      const result = await response.json() as { id?: number; detail?: string; message?: string };
      if (!response.ok) { setMessage(result.detail || result.message || "Content could not be saved."); setSavedMessage("Save failed"); return; }
      if (!initial && pendingMediaId && result.id) {
        const featured = await fetch(`/api/admin/featured-image/${result.id}`, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": token.csrfToken }, body: JSON.stringify({ media_id: pendingMediaId }) });
        if (!featured.ok) { setMessage("Content was saved, but the featured image could not be attached. Retry from the editor."); }
      }
      setDirty(false); setSavedMessage(intent === "publish" ? "Published successfully" : intent === "schedule" ? "Post scheduled" : "All changes saved");
      router.replace(`/admin/${kind}/${result.id}/edit`); router.refresh();
    } catch { setMessage("Content service is temporarily unavailable."); setSavedMessage("Save failed"); }
    finally { setBusy(false); }
  }
  async function action(name: "unpublish" | "trash" | "duplicate") {
    if (!initial || busy) return; setBusy(true); setMessage("");
    try {
      const token = await csrf();
      const response = await fetch(`/api/admin/content/${kind}/${initial.id}/${name}`, { method: "POST", headers: { "X-CSRF-Token": token.csrfToken } });
      const result = await response.json() as { id?: number };
      if (!response.ok) { setMessage("Action could not be completed."); return; }
      if (name === "duplicate" && result.id) router.push(`/admin/posts/${result.id}/edit`);
      else if (name === "trash") router.push("/admin/posts?status=trash");
      else router.refresh();
    } catch { setMessage("Content service is temporarily unavailable."); }
    finally { setBusy(false); }
  }

  return <form className="editor-form" onSubmit={submit} onChange={() => { setDirty(true); setSavedMessage("Unsaved changes"); }}>
    <header className="editor-header">
      <div><div className="editor-kicker"><span>{kind === "posts" ? "POST" : "PAGE"} #{initial?.id || "NEW"}</span><span className={`status-badge ${displayStatus}`}><i />{displayStatus}</span><span className="header-seo">SEO <b>{seo?.seo_score || 0}</b></span></div><h1>{title || (initial ? `Untitled ${kind === "posts" ? "post" : "page"}` : `Create a new ${kind === "posts" ? "post" : "page"}`)}</h1><p>Last updated {dateTime(initial?.updated_at)}</p></div>
      <div className="header-actions"><button type="submit" name="intent" value="draft" className="secondary-button" disabled={busy || isTrashed}>Save Draft</button><button type="button" className="secondary-button" onClick={() => document.getElementById("post-workbench")?.scrollIntoView({ behavior: "smooth" })}>Preview</button><button type="submit" name="intent" value={isPublished ? "save" : "publish"} className="primary-button" disabled={busy || isTrashed}>{isPublished ? "Update" : "Publish"}</button></div>
    </header>
    <div className="editor-grid">
      <div className="editor-main">
        <section className="editor-card core-fields"><div className="card-heading"><div><h2>Article</h2><p>Write clean, structured market coverage.</p></div><span className={`save-indicator ${dirty ? "dirty" : ""}`}><i />{savedMessage}</span></div>
          <label>Title<input name="title" value={title} onChange={e => setTitle(e.target.value)} required maxLength={240} placeholder="Add a clear post title" /></label>
          <div className="field-row"><label>Slug<input name="slug" value={slug} onChange={e => setSlug(e.target.value)} maxLength={160} pattern="[a-z0-9-]*" placeholder="generated-from-title" /></label><span className="field-hint">Lowercase letters, numbers and hyphens</span></div>
          <label>Excerpt<textarea name="excerpt" value={excerpt} onChange={e => setExcerpt(e.target.value)} rows={3} maxLength={2000} placeholder="A concise summary for search and post cards" /></label>
          <label>Article body<span className="editor-help">Lightweight formatting: # H1, ## H2, ### H3, lists, &gt; quotes and Markdown links.</span><textarea name="body" value={body} onChange={e => setBody(e.target.value)} rows={22} maxLength={200000} placeholder="Start writing…" /></label>
          <footer className="editor-stats word-count"><span>{words.toLocaleString("en-IN")} words</span><span>{minutes} min read</span><span>{body.length.toLocaleString("en-IN")} characters</span></footer>
        </section>
        <SeoWorkbench initial={seo || null} content={initial ? { ...initial, title, excerpt, body, slug } : null} kind={kind} categories={categories} publicUrl={publicUrl} />
      </div>
      <aside className="editor-side">
        <section className="editor-card publish-card"><div className="card-heading"><div><h2>Publish</h2><p>Visibility and timing</p></div></div>
          <label>Status<select name="status" defaultValue={isPublished ? "published" : "draft"} disabled={isTrashed}><option value="draft">Draft</option><option value="published">Published</option></select></label>
          <label>Scheduled date<input name="scheduled_at" type="datetime-local" value={scheduledAt} onChange={event => setScheduledAt(event.target.value)} disabled={isTrashed} /></label>
          <div className="publish-buttons"><button className="primary-button" name="intent" value={isPublished ? "save" : "publish"} disabled={busy || isTrashed}>{busy ? "Working…" : isPublished ? "Update post" : "Publish now"}</button><button className="secondary-button" name="intent" value="schedule" disabled={busy || isTrashed || !canSchedule} title={!canSchedule ? "Choose a future date to schedule" : undefined}>Schedule</button></div>
          {isPublished && <button className="text-button" type="button" onClick={() => action("unpublish")} disabled={busy}>Unpublish</button>}
          {message && <div className="form-error" role="alert">{message}</div>}
        </section>
        <section className="editor-card"><div className="card-heading"><div><h2>Organization</h2></div></div><label>Category<select name="category_id" defaultValue={initial?.category_id || ""}><option value="">Uncategorized</option>{categories.map(c => <option value={c.id} key={c.id}>{c.title}</option>)}</select></label><label>Subcategory<input name="subcategory" defaultValue={initial?.subcategory || ""} maxLength={120} /></label><label>Author<input value={initial?.author || "Current administrator"} readOnly aria-describedby="author-note" /></label><small id="author-note" className="support-note">Author reassignment is not supported by the current API.</small></section>
        <FeaturedImagePicker contentId={initial?.id} initial={{ id: initial?.featured_media_id || null, url: initial?.featured_image || null, alt: initial?.featured_image_alt || "" }} onPendingChange={setPendingMediaId} />
        <section className="editor-card seo-side-card"><div className="score-ring" style={{ "--score": `${seo?.seo_score || 0}%` } as CSSProperties}><strong>{seo?.seo_score || 0}</strong><small>/ 100</small></div><div><h2>SEO score</h2><p>Deterministic checks; no ranking guarantee.</p></div></section>
        <section className="editor-card public-card"><h2>Public URL</h2><code>{publicUrl}</code>{isPublished && publicWebsiteUrl && <a href={publicUrl} target="_blank" rel="noreferrer" className="secondary-button">Open Public Post ↗</a>}</section>
        {initial && <section className="danger-actions"><button type="button" onClick={() => action("duplicate")} disabled={busy}>Duplicate post</button>{!isTrashed && <button type="button" className="danger-link" onClick={() => action("trash")} disabled={busy}>Move to Trash</button>}</section>}
      </aside>
    </div>
  </form>;
}
