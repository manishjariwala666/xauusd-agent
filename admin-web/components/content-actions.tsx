"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function ContentActions({ kind, id, status }: {
  kind: "posts" | "pages"; id: number; status: string;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function action(name: "publish" | "unpublish" | "trash") {
    if (busy) return;
    setBusy(true); setMessage("");
    try {
      const csrf = await fetch("/api/admin/auth/csrf", { cache: "no-store" }).then(r => r.json()) as { csrfToken: string };
      const response = await fetch(`/api/admin/content/${kind}/${id}/${name}`, {
        method: "POST", headers: { "X-CSRF-Token": csrf.csrfToken }
      });
      if (!response.ok) { setMessage("Action could not be completed."); return; }
      router.refresh();
    } catch { setMessage("Content service is temporarily unavailable."); }
    finally { setBusy(false); }
  }
  return <div className="row-actions">
    <a href={`/admin/${kind}/${id}/edit`}>Edit</a>
    {status === "published"
      ? <button disabled={busy} onClick={() => action("unpublish")}>Unpublish</button>
      : status !== "trash" && <button disabled={busy} onClick={() => action("publish")}>Publish</button>}
    {kind === "posts" && status !== "trash" && <button disabled={busy} onClick={() => action("trash")}>Trash</button>}
    {message && <small className="action-error" role="alert">{message}</small>}
  </div>;
}
