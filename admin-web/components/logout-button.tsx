"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function LogoutButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function logout() {
    if (busy) return;
    setBusy(true);
    try {
      const csrf = await fetch("/api/admin/auth/csrf", { cache: "no-store" }).then((response) => response.json()) as { csrfToken: string };
      await fetch("/api/admin/auth/logout", { method: "POST", headers: { "X-CSRF-Token": csrf.csrfToken } });
    } finally {
      router.replace("/admin/login");
      router.refresh();
    }
  }

  return <button className="quiet-button" disabled={busy} onClick={logout}>{busy ? "Signing out…" : "Sign out"}</button>;
}
