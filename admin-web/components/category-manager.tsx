"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import type { Category } from "@/lib/content-api";

async function csrfToken() {
  return fetch("/api/admin/auth/csrf", { cache: "no-store" }).then(r => r.json()).then((r: { csrfToken: string }) => r.csrfToken);
}

export function CategoryManager({ categories }: { categories: Category[] }) {
  const router = useRouter(); const [editing, setEditing] = useState<Category | null>(null);
  const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setMessage(""); const form = event.currentTarget; const data = new FormData(form);
    const payload = { title: data.get("title"), slug: data.get("slug"), description: data.get("description"), display_order: Number(data.get("display_order") || 0), is_public: data.get("is_public") === "on", is_active: data.get("is_active") === "on" };
    const endpoint = editing ? `/api/admin/content/categories/${editing.id}` : "/api/admin/content/categories";
    try { const response = await fetch(endpoint, { method: editing ? "PATCH" : "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": await csrfToken() }, body: JSON.stringify(payload) }); const result = await response.json(); if (!response.ok) { setMessage(result.detail || "Category could not be saved."); return; } setEditing(null); form.reset(); router.refresh(); }
    catch { setMessage("Category service is temporarily unavailable."); } finally { setBusy(false); }
  }
  async function disable(id: number) { setBusy(true); try { await fetch(`/api/admin/content/categories/${id}/disable`, { method: "POST", headers: { "X-CSRF-Token": await csrfToken() } }); router.refresh(); } finally { setBusy(false); } }
  return <><section className="page-heading"><small>CONTENT CMS</small><h1>Categories</h1><p>Create, edit and safely disable website categories.</p></section><div className="category-layout"><form className="category-form" onSubmit={submit} key={editing?.id || "new"}><h2>{editing ? "Edit category" : "Add category"}</h2><label>Name<input name="title" required maxLength={160} defaultValue={editing?.title || ""} /></label><label>Slug<input name="slug" maxLength={160} pattern="[a-z0-9-]*" defaultValue={editing?.slug || ""} /></label><label>Description<textarea name="description" rows={5} maxLength={2000} defaultValue={editing?.description || ""} /></label><label>Order<input name="display_order" type="number" min="0" max="100000" defaultValue={editing?.display_order || 0} /></label><label className="check-label"><input name="is_public" type="checkbox" defaultChecked={editing?.is_public ?? true} /> Public</label><label className="check-label"><input name="is_active" type="checkbox" defaultChecked={editing?.is_active ?? true} /> Active</label>{message && <div className="form-error">{message}</div>}<button className="primary-button" disabled={busy}>{busy ? "Saving…" : "Save category"}</button>{editing && <button type="button" className="secondary-button" onClick={() => setEditing(null)}>Cancel</button>}</form><div className="category-list">{categories.length ? categories.map(category => <article key={category.id}><div><strong>{category.title}</strong><code>/{category.slug}</code><p>{category.description || "No description"}</p><span className={`status-badge ${category.is_active ? "published" : "trash"}`}>{category.is_active ? "active" : "inactive"}</span></div><div className="row-actions"><button onClick={() => setEditing(category)}>Edit</button>{category.is_active && <button disabled={busy} onClick={() => disable(category.id)}>Disable</button>}</div></article>) : <section className="state-panel"><strong>No categories</strong></section>}</div></div></>;
}
