"use client";

import { useState } from "react";

type RepairPreview = {
  content_id: number;
  title: string;
  slug: string;
  excerpt: string;
  body: string;
  meta_title: string;
  meta_description: string;
  focus_keyword: string;
  faq: Array<{ question: string; answer: string }>;
  schema_jsonld: Record<string, unknown>;
  status: string;
  published_at?: string | null;
  review_required?: boolean;
};

const choices = [
  ["title", "Title"], ["structure", "Structure"], ["repetition", "Repetition"],
  ["table", "Table"], ["faq", "FAQ"], ["seo", "SEO"], ["readability", "Readability"],
] as const;

async function csrfToken() {
  const response = await fetch("/api/admin/auth/csrf", { cache: "no-store" });
  if (!response.ok) throw new Error("CSRF unavailable");
  return ((await response.json()) as { csrfToken: string }).csrfToken;
}

export function AIContentRepair({ contentId, currentStatus }: { contentId: number; currentStatus: string }) {
  const [selected, setSelected] = useState<string[]>(["structure", "repetition", "readability"]);
  const [preview, setPreview] = useState<RepairPreview | null>(null);
  const [busy, setBusy] = useState<"preview" | "apply" | null>(null);
  const [message, setMessage] = useState("");

  async function requestPreview() {
    if (!selected.length || busy) return;
    setBusy("preview"); setMessage("");
    try {
      const token = await csrfToken();
      const response = await fetch(`/api/admin/content/posts/${contentId}/repair-preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
        body: JSON.stringify({ options: selected }),
      });
      const result = (await response.json()) as RepairPreview & { message?: string };
      if (!response.ok) { setMessage(result.message || "Repair preview could not be created."); return; }
      setPreview(result);
    } catch { setMessage("Repair service is temporarily unavailable."); }
    finally { setBusy(null); }
  }

  async function applyPreview() {
    if (!preview || busy) return;
    setBusy("apply"); setMessage("");
    try {
      const token = await csrfToken();
      const response = await fetch(`/api/admin/content/posts/${contentId}/repair-apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
        body: JSON.stringify({
          title: preview.title,
          slug: preview.slug,
          excerpt: preview.excerpt,
          body: preview.body,
          meta_title: preview.meta_title,
          meta_description: preview.meta_description,
          focus_keyword: preview.focus_keyword,
          faq: preview.faq,
          schema_jsonld: preview.schema_jsonld,
        }),
      });
      const result = (await response.json()) as { id?: number; status?: string; message?: string };
      if (!response.ok) { setMessage(result.message || "Reviewed repair could not be applied."); return; }
      if (result.id !== contentId || result.status !== currentStatus) {
        setMessage("Safety check failed: post identity or status changed.");
        return;
      }
      window.location.reload();
    } catch { setMessage("Repair service is temporarily unavailable."); }
    finally { setBusy(null); }
  }

  function updatePreview<Key extends keyof RepairPreview>(
    key: Key,
    value: RepairPreview[Key]
  ) {
    setPreview((current) => current ? { ...current, [key]: value } : current);
  }

  return <section className="editor-card ai-repair-card">
    <div className="card-heading"><div><h2>AI Repair</h2><p>Preview first. The same post ID, status and dates are preserved.</p></div></div>
    <div className="ai-repair-options">{choices.map(([value, label]) => <label key={value}><input type="checkbox" checked={selected.includes(value)} onChange={(event) => setSelected(event.target.checked ? [...selected, value] : selected.filter(item => item !== value))} />{label}</label>)}</div>
    <button type="button" className="secondary-button" disabled={!selected.length || Boolean(busy)} onClick={requestPreview}>{busy === "preview" ? "Reviewing…" : "Create repair preview"}</button>
    {busy === "preview" && <p className="ai-inline-status" role="status" aria-live="polite"><span className="ai-loading-spinner" aria-hidden="true" />Preparing a review-only repair. The post is unchanged.</p>}
    {preview && <div className="ai-repair-preview">
      <strong>Review and edit before save</strong>
      <p className="support-note">Post #{preview.content_id} remains <b>{preview.status}</b>. Applying this review does not publish, unpublish or change its original publication date.</p>
      <label>Repaired title<input value={preview.title} maxLength={240} disabled={Boolean(busy)} onChange={(event) => updatePreview("title", event.target.value)} /></label>
      <label>Slug<input value={preview.slug} maxLength={160} disabled={Boolean(busy)} onChange={(event) => updatePreview("slug", event.target.value)} /></label>
      <label>Excerpt<textarea rows={3} value={preview.excerpt} maxLength={2_000} disabled={Boolean(busy)} onChange={(event) => updatePreview("excerpt", event.target.value)} /></label>
      <label>Article body<textarea rows={14} value={preview.body} maxLength={200_000} disabled={Boolean(busy)} onChange={(event) => updatePreview("body", event.target.value)} /></label>
      <label>Meta title<input value={preview.meta_title} maxLength={255} disabled={Boolean(busy)} onChange={(event) => updatePreview("meta_title", event.target.value)} /></label>
      <label>Meta description<textarea rows={3} value={preview.meta_description} maxLength={500} disabled={Boolean(busy)} onChange={(event) => updatePreview("meta_description", event.target.value)} /></label>
      <label>Focus keyword<input value={preview.focus_keyword} maxLength={160} disabled={Boolean(busy)} onChange={(event) => updatePreview("focus_keyword", event.target.value)} /></label>
      <dl><div><dt>Body</dt><dd>{preview.body.length.toLocaleString("en-IN")} characters</dd></div><div><dt>FAQs</dt><dd>{preview.faq.length}</dd></div></dl>
      <details className="ai-repair-structured-review">
        <summary>Review repaired FAQ content ({preview.faq.length})</summary>
        {preview.faq.length ? (
          <ol>{preview.faq.map((item, index) => <li key={`${index}-${item.question}`}><strong>{item.question}</strong><p>{item.answer}</p></li>)}</ol>
        ) : <p>No FAQ entries are included in this repair.</p>}
      </details>
      <details className="ai-repair-structured-review">
        <summary>Review structured data</summary>
        <pre>{JSON.stringify(preview.schema_jsonld, null, 2)}</pre>
      </details>
      <div className="ai-repair-actions"><button type="button" className="secondary-button" disabled={Boolean(busy)} onClick={() => setPreview(null)}>Discard preview</button><button type="button" className="primary-button" disabled={Boolean(busy) || !preview.title.trim() || !preview.body.trim()} onClick={applyPreview}>{busy === "apply" ? "Applying…" : "Apply reviewed repair"}</button></div>
      {busy === "apply" && <p className="ai-inline-status" role="status" aria-live="polite"><span className="ai-loading-spinner" aria-hidden="true" />Saving only the reviewed fields while preserving lifecycle status.</p>}
    </div>}
    {message && <p className="form-error" role="alert">{message}</p>}
  </section>;
}
