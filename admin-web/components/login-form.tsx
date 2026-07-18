"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export function LoginForm() {
  const router = useRouter();
  const [csrfToken, setCsrfToken] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    fetch("/api/admin/auth/csrf", { cache: "no-store" })
      .then((response) => response.ok ? response.json() : Promise.reject())
      .then((payload: { csrfToken?: string }) => {
        if (active) setCsrfToken(payload.csrfToken || "");
      })
      .catch(() => {
        if (active) setMessage("Secure login initialization failed. Please refresh.");
      });
    return () => { active = false; };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!csrfToken || submitting) return;
    setSubmitting(true);
    setMessage("");
    const data = new FormData(event.currentTarget);
    try {
      const response = await fetch("/api/admin/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
        body: JSON.stringify({ email: data.get("email"), password: data.get("password") })
      });
      const payload = (await response.json()) as { message?: string };
      if (response.status === 403) {
        router.replace("/admin/forbidden");
        return;
      }
      if (!response.ok) {
        setMessage(payload.message || "Invalid email or password.");
        return;
      }
      router.replace("/admin/dashboard");
      router.refresh();
    } catch {
      setMessage("Admin login is temporarily unavailable.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="login-form" onSubmit={submit}>
      <label htmlFor="email">Email address</label>
      <input id="email" name="email" type="email" autoComplete="username" required maxLength={320} />
      <label htmlFor="password">Password</label>
      <input id="password" name="password" type="password" autoComplete="current-password" required maxLength={128} />
      {message ? <div className="form-error" role="alert">{message}</div> : null}
      <button className="primary-button" disabled={!csrfToken || submitting} type="submit">
        {submitting ? "Signing in…" : "Sign in securely"}
      </button>
    </form>
  );
}
