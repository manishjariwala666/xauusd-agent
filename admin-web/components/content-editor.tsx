"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { Category, ContentDetail } from "@/lib/content-api";

export function ContentEditor({ kind, initial, categories }: {
  kind: "posts" | "pages"; initial?: ContentDetail | null; categories: Category[];
}) {
  const router = useRouter();
  const [body, setBody] = useState(initial?.body || "");
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const words = useMemo(() => body.trim() ? body.trim().split(/\s+/).length : 0, [body]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (dirty) event.preventDefault(); };
    addEventListener("beforeunload", warn); return () => removeEventListener("beforeunload", warn);
  }, [dirty]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return; setBusy(true); setMessage("");
    const data = new FormData(event.currentTarget);
    const payload = Object.fromEntries(data.entries());
    payload.body = body;
    payload.category_id = payload.category_id ? Number(payload.category_id) as never : null as never;
    payload.scheduled_at = payload.scheduled_at ? new Date(String(payload.scheduled_at)).toISOString() as never : null as never;
    try {
      const csrf = await fetch("/api/admin/auth/csrf", { cache: "no-store" }).then(r => r.json()) as { csrfToken: string };
      const endpoint = initial ? `/api/admin/content/${kind}/${initial.id}` : `/api/admin/content/${kind}`;
      const response = await fetch(endpoint, { method: initial ? "PATCH" : "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf.csrfToken }, body: JSON.stringify(payload) });
      const result = await response.json() as { id?: number; detail?: string; message?: string };
      if (!response.ok) { setMessage(result.detail || result.message || "Content could not be saved."); return; }
      setDirty(false); router.replace(`/admin/${kind}/${result.id}/edit`); router.refresh();
    } catch { setMessage("Content service is temporarily unavailable."); }
    finally { setBusy(false); }
  }
  return <form className="editor-form" onSubmit={submit} onChange={() => setDirty(true)}><section className="page-heading"><small>CONTENT EDITOR</small><h1>{initial ? "Edit" : "Create"} {kind === "posts" ? "post" : "page"}</h1></section><div className="editor-grid"><div className="editor-main"><label>Title<input name="title" defaultValue={initial?.title || ""} required maxLength={240} /></label><label>Slug<input name="slug" defaultValue={initial?.slug || ""} maxLength={160} pattern="[a-z0-9-]*" placeholder="generated-from-title" /></label><label>Excerpt<textarea name="excerpt" defaultValue={initial?.excerpt || ""} rows={3} maxLength={2000} /></label><label>Body<textarea name="body" value={body} onChange={e => { setBody(e.target.value); setDirty(true); }} rows={20} maxLength={200000} /></label><div className="word-count">{words} words</div></div><aside className="editor-side"><label>Status<select name="status" defaultValue={initial?.status === "published" ? "published" : "draft"}><option value="draft">Draft</option><option value="published">Published</option></select></label><label>Category<select name="category_id" defaultValue={initial?.category_id || ""}><option value="">Uncategorized</option>{categories.map(c => <option value={c.id} key={c.id}>{c.title}</option>)}</select></label><label>Subcategory<input name="subcategory" defaultValue={initial?.subcategory || ""} maxLength={120} /></label><label>Schedule date<input name="scheduled_at" type="datetime-local" defaultValue={initial?.scheduled_at ? initial.scheduled_at.slice(0,16) : ""} /></label>{message && <div className="form-error" role="alert">{message}</div>}<button className="primary-button" disabled={busy}>{busy ? "Saving…" : "Save content"}</button>{dirty && <small className="unsaved">Unsaved changes</small>}</aside></div></form>;
}
