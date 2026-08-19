"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

const csrf = async () => fetch("/api/admin/auth/csrf", { cache: "no-store" }).then(response => response.json()) as Promise<{ csrfToken: string }>;

export function SignalActions({ id, state }: { id: number; state: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function run(path: string, body?: Record<string, unknown>, confirmText?: string) {
    if (confirmText && !window.confirm(confirmText)) return;
    setBusy(true); setMessage("");
    try {
      const { csrfToken } = await csrf();
      const response = await fetch(`/api/admin/signals/${id}/${path}`, {
        method: "POST", headers: { "X-CSRF-Token": csrfToken, ...(body ? { "Content-Type": "application/json" } : {}) }, body: body ? JSON.stringify(body) : undefined
      });
      const result = await response.json() as { id?: number; detail?: string; message?: string };
      if (!response.ok) { setMessage(result.detail || result.message || "Action failed."); return; }
      if (path === "duplicate" && result.id) router.push(`/admin/signals/${result.id}/edit`);
      else router.refresh();
    } catch { setMessage("Signals service is temporarily unavailable."); }
    finally { setBusy(false); }
  }
  return <div className="signal-row-actions">
    <a href={`/admin/signals/${id}/edit`}>Edit</a>
    <button disabled={busy} onClick={() => run("duplicate")}>Duplicate</button>
    {state === "DRAFT" && <button disabled={busy} onClick={() => run("publish", undefined, "Publish this signal publicly?")}>Publish</button>}
    {state === "PUBLISHED" && <button disabled={busy} onClick={() => run("transition", { action: "ACTIVATE" }, "Mark this signal active?")}>Activate</button>}
    {state === "ACTIVE" && <button disabled={busy} onClick={() => run("transition", { action: "TARGET_HIT" }, "Mark a target hit? Verify the stored result first.")}>Target hit</button>}
    {state !== "TRASHED" && <button className="danger-link" disabled={busy || state === "ACTIVE"} title={state === "ACTIVE" ? "Close or cancel an active signal first." : undefined} onClick={() => run("trash", undefined, "Move this signal to trash?")}>Trash</button>}
    {state === "TRASHED" && <button disabled={busy} onClick={() => run("restore")}>Restore</button>}
    {message && <small role="alert">{message}</small>}
  </div>;
}
