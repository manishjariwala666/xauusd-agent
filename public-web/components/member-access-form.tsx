"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

export type MemberAccessMode = "login" | "signup" | "forgot" | "reset" | "verify";

type ApiResult = { detail?: string; message?: string; user?: { payment_status?: string } };

async function post(path: string, body: Record<string, string>): Promise<{ ok: boolean; data: ApiResult }> {
  try {
    const response = await fetch(`/api/member/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      credentials: "same-origin",
      cache: "no-store",
    });
    const data = (await response.json().catch(() => ({}))) as ApiResult;
    return { ok: response.ok, data };
  } catch {
    return {
      ok: false,
      data: { detail: "Member service is temporarily unavailable. Please try again." },
    };
  }
}

export function MemberAccessForm({ mode }: { mode: MemberAccessMode }) {
  const router = useRouter();
  const params = useSearchParams();
  const token = useMemo(() => params.get("token") || "", [params]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;

    setBusy(true);
    setMessage("");
    setError("");
    const form = new FormData(event.currentTarget);
    const value = (name: string) => String(form.get(name) || "").trim();

    try {
      let result: { ok: boolean; data: ApiResult };
      if (mode === "login") {
        result = await post("auth/login", { email: value("email"), password: String(form.get("password") || "") });
        if (result.ok) {
          const sessionCheck = await fetch("/api/member/auth/me", {
            method: "GET",
            cache: "no-store",
            credentials: "same-origin",
          }).catch(() => null);

          if (!sessionCheck?.ok) {
            setError("Sign-in succeeded, but the member session could not be initialized. Please try again.");
            return;
          }

          router.replace("/signals");
          router.refresh();
          return;
        }
      } else if (mode === "signup") {
        result = await post("auth/signup", {
          email: value("email"),
          password: String(form.get("password") || ""),
          confirm_password: String(form.get("confirm_password") || ""),
          whatsapp: value("whatsapp"),
          transaction_id: value("transaction_id"),
        });
      } else if (mode === "forgot") {
        result = await post("auth/forgot-password", { email: value("email") });
      } else if (mode === "verify") {
        result = await post("auth/verify-email", { token });
      } else {
        result = await post("auth/reset-password", {
          token,
          password: String(form.get("password") || ""),
          confirm_password: String(form.get("confirm_password") || ""),
        });
      }

      if (result.ok) setMessage(result.data.message || "Request completed successfully.");
      else setError(result.data.detail || "Request could not be completed.");
    } catch {
      setError("Something went wrong while contacting the member service. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  if ((mode === "reset" || mode === "verify") && !token) {
    return <p className="auth-error">This link is missing its security token.</p>;
  }

  return <form className="auth-form" onSubmit={submit} noValidate={false}>
    {(mode === "login" || mode === "signup" || mode === "forgot") && <label>Email<input name="email" type="email" autoComplete="email" required /></label>}
    {mode === "signup" && <label>WhatsApp number<input name="whatsapp" type="tel" autoComplete="tel" required /></label>}
    {(mode === "login" || mode === "signup" || mode === "reset") && <label>Password<input name="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={mode === "login" ? 1 : 12} required /></label>}
    {(mode === "signup" || mode === "reset") && <label>Confirm password<input name="confirm_password" type="password" autoComplete="new-password" minLength={12} required /></label>}
    {mode === "signup" && <label>USDT TXID <span>(optional at signup)</span><input name="transaction_id" type="text" maxLength={200} /></label>}
    <button className="button button-dark" type="submit" disabled={busy} aria-busy={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : mode === "signup" ? "Create account" : mode === "forgot" ? "Send reset link" : mode === "verify" ? "Verify email" : "Reset password"}</button>
    {message && <p className="auth-success" role="status">{message}</p>}
    {error && <p className="auth-error" role="alert">{error}</p>}
    {mode === "login" && <p><Link href="/forgot-password">Forgot password?</Link> · <Link href="/signup">Create account</Link></p>}
    {mode === "signup" && <p><Link href="/login">Already have an account?</Link></p>}
  </form>;
}
