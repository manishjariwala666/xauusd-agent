"use client";

import { FormEvent, useEffect, useMemo, useState, type CSSProperties } from "react";
import { useRouter } from "next/navigation";
import type { Category, ContentDetail } from "@/lib/content-api";
import { SafeContentPreview } from "./safe-content-preview";

type Tab = "preview" | "seo" | "og" | "faq" | "metadata";
type Intent = "save" | "draft" | "publish" | "schedule";
const tabs: Array<[Tab, string]> = [["preview", "Post Preview"], ["seo", "SEO Settings"], ["og", "Open Graph"], ["faq", "FAQ / Schema"], ["metadata", "Content Metadata"]];
const dateTime = (value?: string | null) => value ? new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "Not set";
const ogValue = (source: Record<string, unknown> | undefined, ...keys: string[]) => keys.map(key => source?.[key]).find(value => typeof value === "string") as string | undefined || "";

export function ContentEditor({ kind, initial, categories, publicWebsiteUrl }: {
  kind: "posts" | "pages"; initial?: ContentDetail | null; categories: Category[]; publicWebsiteUrl?: string;
}) {
  const router = useRouter();
  const [title, setTitle] = useState(initial?.title || "");
  const [slug, setSlug] = useState(initial?.slug || "");
  const [excerpt, setExcerpt] = useState(initial?.excerpt || "");
  const [body, setBody] = useState(initial?.body || "");
  const [scheduledAt, setScheduledAt] = useState(initial?.scheduled_at ? initial.scheduled_at.slice(0, 16) : "");
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [savedMessage, setSavedMessage] = useState(initial ? "All changes saved" : "New unsaved content");
  const [tab, setTab] = useState<Tab>("preview");
  const words = useMemo(() => body.trim() ? body.replace(/<[^>]+>/g, " ").trim().split(/\s+/).length : 0, [body]);
  const minutes = Math.max(1, Math.ceil(words / 220));
  const publicUrl = publicWebsiteUrl && slug ? `${publicWebsiteUrl}/${kind === "posts" ? "blog" : "page"}/${encodeURIComponent(slug)}` : "Public URL is not configured locally";
  const isPublished = initial?.status === "published";
  const isTrashed = initial?.status === "trash";
  const displayStatus = !isPublished && !isTrashed && initial?.scheduled_at && new Date(initial.scheduled_at) > new Date() ? "scheduled" : initial?.status || "draft";
  const canSchedule = Boolean(scheduledAt) && new Date(scheduledAt) > new Date();
  const seoTitle = initial?.meta_title || title;
  const metaDescription = initial?.meta_description || excerpt;
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
      <div><div className="editor-kicker"><span>POST #{initial?.id || "NEW"}</span><span className={`status-badge ${displayStatus}`}><i />{displayStatus}</span><span className="header-seo">SEO <b>{initial?.seo_score || 0}</b></span></div><h1>{title || (initial ? "Untitled post" : "Create a new post")}</h1><p>Last updated {dateTime(initial?.updated_at)}</p></div>
      <div className="header-actions"><button type="submit" name="intent" value="draft" className="secondary-button" disabled={busy || isTrashed}>Save Draft</button><button type="button" className="secondary-button" onClick={() => { setTab("preview"); document.getElementById("post-workbench")?.scrollIntoView({ behavior: "smooth" }); }}>Preview</button><button type="submit" name="intent" value={isPublished ? "save" : "publish"} className="primary-button" disabled={busy || isTrashed}>{isPublished ? "Update" : "Publish"}</button></div>
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
        <section className="editor-card workbench" id="post-workbench"><div className="tab-list" role="tablist" aria-label="Post optimization panels">{tabs.map(([value, label]) => <button type="button" role="tab" aria-selected={tab === value} className={tab === value ? "active" : ""} onClick={() => setTab(value)} key={value}>{label}</button>)}</div>
          <div className="tab-panel" role="tabpanel">
            {tab === "preview" && <div className="preview-stack"><div className="google-preview"><small>Google search preview</small><a>{seoTitle || "Post title preview"}</a><span>{publicUrl}</span><p>{metaDescription || "Add an excerpt or meta description to preview the search snippet."}</p></div><div className="content-preview-card"><div className="preview-label">Article preview <span>Sanitized</span></div><SafeContentPreview body={body} title={title} /></div></div>}
            {tab === "seo" && <UnsupportedSeo initial={initial} slug={slug} publicUrl={publicUrl} />}
            {tab === "og" && <OpenGraphPanel initial={initial} />}
            {tab === "faq" && <FaqSchemaPanel initial={initial} />}
            {tab === "metadata" && <MetadataPanel initial={initial} kind={kind} categories={categories} />}
          </div>
        </section>
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
        <section className="editor-card featured-card"><div className="card-heading"><div><h2>Featured image</h2></div><span className="coming-badge">Media later</span></div><div className="featured-placeholder" style={initial?.featured_image ? { backgroundImage: `url(${initial.featured_image})` } : undefined}>{!initial?.featured_image && <><b>▧</b><span>No featured image</span><small>Managed by the future Media phase</small></>}</div></section>
        <section className="editor-card seo-side-card"><div className="score-ring" style={{ "--score": `${initial?.seo_score || 0}%` } as CSSProperties}><strong>{initial?.seo_score || 0}</strong><small>/ 100</small></div><div><h2>SEO score</h2><p>Based on existing SEO metadata.</p></div></section>
        <section className="editor-card public-card"><h2>Public URL</h2><code>{publicUrl}</code>{isPublished && publicWebsiteUrl && <a href={publicUrl} target="_blank" rel="noreferrer" className="secondary-button">Open Public Post ↗</a>}</section>
        {initial && <section className="danger-actions"><button type="button" onClick={() => action("duplicate")} disabled={busy}>Duplicate post</button>{!isTrashed && <button type="button" className="danger-link" onClick={() => action("trash")} disabled={busy}>Move to Trash</button>}</section>}
      </aside>
    </div>
  </form>;
}

function UnsupportedSeo({ initial, slug, publicUrl }: { initial?: ContentDetail | null; slug: string; publicUrl: string }) {
  const validations = [initial?.meta_title ? "SEO title is available" : "Add an SEO title in a future SEO editing phase", initial?.meta_description ? "Meta description is available" : "Meta description falls back to the excerpt", initial?.focus_keyword ? "Focus keyword is available" : "No focus keyword is stored"];
  return <div className="seo-form"><div className="readonly-notice"><strong>Read-only SEO data</strong><span>The current content API exposes these values but does not safely update them yet.</span></div><label>SEO title<input value={initial?.meta_title || ""} readOnly placeholder="Not set" /></label><label>Meta description<textarea value={initial?.meta_description || ""} readOnly rows={3} placeholder="Not set" /></label><div className="two-fields"><label>Focus keyword<input value={initial?.focus_keyword || ""} readOnly placeholder="Not set" /></label><label>Slug<input value={slug} readOnly /></label></div><label>Canonical URL<input value={publicUrl} readOnly /></label><label>Robots setting<input value="Inherited from site defaults" readOnly /></label><div className="seo-validation"><h3>Validation</h3>{validations.map((item, index) => <p key={item} className={index === 0 && initial?.meta_title ? "valid" : "notice"}><span>{index === 0 && initial?.meta_title ? "✓" : "!"}</span>{item}</p>)}</div></div>;
}

function OpenGraphPanel({ initial }: { initial?: ContentDetail | null }) {
  return <div className="seo-form"><div className="readonly-notice"><strong>Read-only social metadata</strong><span>Values come from existing content_seo data. Editing is planned for the full SEO phase.</span></div><label>OG title<input value={ogValue(initial?.open_graph, "title", "og_title")} readOnly placeholder="Not set" /></label><label>OG description<textarea value={ogValue(initial?.open_graph, "description", "og_description")} readOnly rows={3} placeholder="Not set" /></label><label>OG image URL<input value={ogValue(initial?.open_graph, "image", "image_url")} readOnly placeholder="Not set" /></label><div className="two-fields"><label>X/Twitter title<input value={ogValue(initial?.twitter_card, "title")} readOnly placeholder="Not set" /></label><label>Card type<input value={ogValue(initial?.twitter_card, "card", "card_type")} readOnly placeholder="Inherited" /></label></div></div>;
}

function FaqSchemaPanel({ initial }: { initial?: ContentDetail | null }) {
  const faq = Array.isArray(initial?.faq) ? initial.faq : [];
  return <div className="schema-panel"><div className="readonly-notice"><strong>Existing structured data</strong><span>Collapsed by default to keep this editor fast and readable.</span></div><details><summary>FAQ data <span>{faq.length} item{faq.length === 1 ? "" : "s"}</span></summary><div className="faq-list">{faq.length ? faq.map((item, index) => <article key={index}><strong>{String(item.question || item.name || `Question ${index + 1}`)}</strong><p>{String(item.answer || item.acceptedAnswer || "No answer value")}</p></article>) : <p>No FAQ data is stored for this post.</p>}</div></details><details><summary>Schema JSON-LD <span>View safely</span></summary><pre>{JSON.stringify(initial?.schema_jsonld || {}, null, 2)}</pre></details></div>;
}

function MetadataPanel({ initial, kind, categories }: { initial?: ContentDetail | null; kind: string; categories: Category[] }) {
  const category = categories.find(item => item.id === initial?.category_id)?.title || initial?.category || "Uncategorized";
  const items = [["Content type", kind === "posts" ? "Blog post" : "Page"], ["Status", initial?.status || "Draft"], ["Category", category], ["Subcategory", initial?.subcategory || "—"], ["Author", initial?.author || "Current administrator"], ["Views", String(initial?.views || 0)], ["Publish date", dateTime(initial?.published_at)], ["Updated date", dateTime(initial?.updated_at)]];
  return <div className="metadata-grid">{items.map(([label, value]) => <article key={label}><small>{label}</small><strong>{value}</strong></article>)}</div>;
}
