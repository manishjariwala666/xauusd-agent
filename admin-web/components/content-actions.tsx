"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function ContentActions({ kind, id, status, previewUrl, previewLabel = "Preview", compact = false }: {
  kind: "posts" | "pages"; id: number; status: string; previewUrl?: string; previewLabel?: string; compact?: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function action(name: "publish" | "unpublish" | "trash" | "duplicate") {
    if (busy) return;
    setBusy(true); setMessage("");
    try {
      const csrf = await fetch("/api/admin/auth/csrf", { cache: "no-store" }).then(r => r.json()) as { csrfToken: string };
      const response = await fetch(`/api/admin/content/${kind}/${id}/${name}`, {
        method: "POST", headers: { "X-CSRF-Token": csrf.csrfToken }
      });
      const result = await response.json() as { id?: number };
      if (!response.ok) { setMessage("Action could not be completed."); return; }
      if (name === "duplicate" && result.id) { router.push(`/admin/posts/${result.id}/edit`); return; }
      router.refresh();
    } catch { setMessage("Content service is temporarily unavailable."); }
    finally { setBusy(false); }
  }
  return <div className={`row-actions ${compact ? "compact" : ""}`}>
    <a href={`/admin/${kind}/${id}/edit`}>{compact ? "Edit" : "Edit post"}</a>
    {previewUrl && <a href={previewUrl} target="_blank" rel="noreferrer">{previewLabel}</a>}
    {status === "published"
      ? <button disabled={busy} onClick={() => action("unpublish")}>Unpublish</button>
      : status !== "trash" && <button disabled={busy} onClick={() => action("publish")}>Publish</button>}
    {kind === "posts" && <button disabled={busy} onClick={() => action("duplicate")}>Duplicate</button>}
    {kind === "posts" && status !== "trash" && <button disabled={busy} onClick={() => action("trash")}>Trash</button>}
    {message && <small className="action-error" role="alert">{message}</small>}
  </div>;
}
