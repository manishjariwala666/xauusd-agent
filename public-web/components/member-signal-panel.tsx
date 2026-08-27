"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import type { Signal, SignalPage } from "@/lib/types";

type MeResponse = { user?: { email?: string; email_verified?: boolean; payment_status?: string; paid_access?: boolean }; detail?: string };
type PaymentResponse = { payment?: { payment_status?: string; transaction_id?: string | null; review_note?: string | null }; instructions?: { network?: string; amount_usdt?: string }; detail?: string };
type AccessResponse = { telegram_invite_url?: string | null; whatsapp_invite_url?: string | null };

const price = (value?: number | string | null) => value == null || value === "" ? "—" : String(value);

export function MemberSignalPanel() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [payment, setPayment] = useState<PaymentResponse | null>(null);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [access, setAccess] = useState<AccessResponse>({});
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState("");

  async function load() {
    setBusy(true);
    const meResponse = await fetch("/api/member/auth/me", { cache: "no-store" });
    if (!meResponse.ok) {
      setMe({ detail: "AUTH_REQUIRED" });
      setBusy(false);
      return;
    }
    const meData = await meResponse.json() as MeResponse;
    setMe(meData);
    if (!meData.user?.paid_access) {
      const paymentResponse = await fetch("/api/member/payment", { cache: "no-store" });
      if (paymentResponse.ok) setPayment(await paymentResponse.json() as PaymentResponse);
      setBusy(false);
      return;
    }
    const [signalResponse, accessResponse] = await Promise.all([
      fetch("/api/member/signals?symbol=XAUUSD&page_size=20", { cache: "no-store" }),
      fetch("/api/member/access", { cache: "no-store" }),
    ]);
    if (signalResponse.ok) {
      const data = await signalResponse.json() as SignalPage;
      setSignals(Array.isArray(data.items) ? data.items : []);
    }
    if (accessResponse.ok) setAccess(await accessResponse.json() as AccessResponse);
    setBusy(false);
  }

  useEffect(() => { void load(); }, []);

  async function submitPayment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const transaction_id = String(form.get("transaction_id") || "").trim();
    const response = await fetch("/api/member/payment/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transaction_id }),
    });
    const data = await response.json().catch(() => ({})) as { detail?: string; message?: string };
    setMessage(response.ok ? data.message || "Payment submitted." : data.detail || "Payment submission failed.");
    if (response.ok) await load();
  }

  async function logout() {
    await fetch("/api/member/auth/logout", { method: "POST" });
    window.location.href = "/login";
  }

  if (busy) return <section className="member-panel"><p>Checking member access…</p></section>;
  if (!me?.user) return <section className="member-panel"><h2>Member access</h2><p>Sign in to view payment status and protected Gold Signals.</p><div className="hero-actions"><Link className="button primary" href="/login">Member login</Link><Link className="button secondary" href="/signup">Create account</Link></div></section>;

  if (!me.user.paid_access) {
    const status = payment?.payment?.payment_status || me.user.payment_status || "NOT_STARTED";
    const pending = status === "PENDING" || status === "UNDER_REVIEW";
    return <section className="member-panel"><div className="section-heading"><div><span className="eyebrow">MEMBER PAYMENT</span><h2>Payment status: {status}</h2></div><button className="button secondary" type="button" onClick={logout}>Logout</button></div>
      <p>Premium signals unlock only after email verification and manual payment approval.</p>
      {payment?.instructions && <p><strong>Amount:</strong> {payment.instructions.amount_usdt || "—"} USDT · <strong>Network:</strong> {payment.instructions.network || "—"}</p>}
      {!pending && <form className="auth-form" onSubmit={submitPayment}><label>USDT transaction ID (TXID)<input name="transaction_id" minLength={8} maxLength={200} required /></label><button className="button button-dark" type="submit">Submit payment for review</button></form>}
      {pending && <p>Your submitted transaction is waiting for administrator review.</p>}
      {payment?.payment?.review_note && <p>{payment.payment.review_note}</p>}
      {message && <p role="status">{message}</p>}
    </section>;
  }

  return <section className="member-panel"><div className="section-heading"><div><span className="eyebrow">VERIFIED MEMBER</span><h2>Protected Gold Signals</h2></div><button className="button secondary" type="button" onClick={logout}>Logout</button></div>
    {(access.telegram_invite_url || access.whatsapp_invite_url) && <div className="hero-actions">{access.telegram_invite_url && <a className="button primary" href={access.telegram_invite_url}>Private Telegram</a>}{access.whatsapp_invite_url && <a className="button secondary" href={access.whatsapp_invite_url}>Private WhatsApp</a>}</div>}
    {signals.length ? <div className="signal-grid">{signals.map((signal) => <article className="signal-card" key={signal.public_id}><div className="signal-card-head"><span>{signal.symbol || "XAUUSD"}</span><span>{signal.direction || signal.signal_type}</span></div><dl><div><dt>Entry</dt><dd>{price(signal.entry_price)}</dd></div><div><dt>Stop loss</dt><dd>{price(signal.stop_loss)}</dd></div><div><dt>Target 1</dt><dd>{price(signal.target_1)}</dd></div><div><dt>Target 2</dt><dd>{price(signal.target_2)}</dd></div><div><dt>Target 3</dt><dd>{price(signal.target_3)}</dd></div><div><dt>Target 4</dt><dd>{price(signal.target_4)}</dd></div></dl>{signal.analysis_summary && <p>{signal.analysis_summary}</p>}{signal.public_id && <Link href={`/signals/${encodeURIComponent(signal.public_id)}`}>Open member detail →</Link>}</article>)}</div> : <div className="empty-state"><h3>No published Gold Signal right now</h3><p>The protected feed shows only canonical published, non-deleted records.</p></div>}
  </section>;
}
