"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";

async function csrf() {
  return fetch("/api/admin/auth/csrf", { cache: "no-store" }).then(response => response.json()) as Promise<{ csrfToken: string }>;
}

export function PublicationActions({ family, id, actions }: { family: "announcements" | "results"; id: number; actions: string[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState("");
  async function run(action: string) {
    if (!confirm(`Confirm ${action.toLowerCase().replaceAll("_", " ")}?`)) return;
    setBusy(action);
    try {
      const { csrfToken } = await csrf();
      const duplicate = action === "DUPLICATE";
      const permanentDelete = action === "DELETE";
      const path = permanentDelete ? `/api/admin/${family}/${id}?confirmed=true` : duplicate ? `/api/admin/${family}/${id}/duplicate` : `/api/admin/${family}/${id}/transition`;
      const response = await fetch(path, {
        method: permanentDelete ? "DELETE" : "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
        body: permanentDelete || duplicate ? undefined : JSON.stringify({ action })
      });
      if (!response.ok) {
        const result = await response.json();
        alert(result.detail || result.message || "Action failed.");
      } else router.refresh();
    } finally { setBusy(""); }
  }
  return <div className="row-actions">{actions.map(action => <button type="button" key={action} disabled={!!busy} onClick={() => run(action)}>{busy === action ? "Working…" : action.replaceAll("_", " ")}</button>)}</div>;
}
