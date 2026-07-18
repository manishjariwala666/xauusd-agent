"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { AdminSignal } from "@/lib/signals-api";

const csrf = async () => fetch("/api/admin/auth/csrf", { cache: "no-store" }).then(response => response.json()) as Promise<{ csrfToken: string }>;
const value = (input: string | null | undefined) => input || "";

export function SignalEditor({ initial }: { initial?: AdminSignal | null }) {
  const router = useRouter();
  const [direction, setDirection] = useState<"BUY" | "SELL">(initial?.signal_type || "BUY");
  const [symbol, setSymbol] = useState(initial?.symbol || "XAUUSD");
  const [entry, setEntry] = useState(value(initial?.price));
  const [stop, setStop] = useState(value(initial?.stop_loss));
  const [targets, setTargets] = useState([value(initial?.target_1), value(initial?.target_2), value(initial?.target_3), value(initial?.target_4)]);
  const [summary, setSummary] = useState(value(initial?.analysis_summary));
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState("");
  const editable = !initial || ["DRAFT", "SCHEDULED"].includes(initial.lifecycle_status);
  const previewTargets = useMemo(() => targets.filter(Boolean).join(" · ") || "Not set", [targets]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!editable || busy) return;
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries()) as Record<string, unknown>;
    payload.symbol = symbol; payload.direction = direction; payload.entry_price = entry; payload.stop_loss = stop || null;
    targets.forEach((target, index) => payload[`target_${index + 1}`] = target || null);
    payload.analysis_summary = summary;
    payload.featured = form.get("featured") === "on";
    for (const key of ["entry_price_min", "entry_price_max", "scheduled_at", "expires_at"]) if (!payload[key]) payload[key] = null;
    if (payload.scheduled_at) payload.scheduled_at = new Date(String(payload.scheduled_at)).toISOString();
    if (payload.expires_at) payload.expires_at = new Date(String(payload.expires_at)).toISOString();
    setBusy(true); setMessage("");
    try {
      const { csrfToken } = await csrf();
      const response = await fetch(initial ? `/api/admin/signals/${initial.id}` : "/api/admin/signals", { method: initial ? "PATCH" : "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken }, body: JSON.stringify(payload) });
      const result = await response.json() as { id?: number; detail?: string; message?: string };
      if (!response.ok) { setMessage(result.detail || result.message || "Signal could not be saved."); return; }
      router.replace(`/admin/signals/${result.id}/edit`); router.refresh();
    } catch { setMessage("Signals service is temporarily unavailable."); }
    finally { setBusy(false); }
  }
  return <form className="editor-form signal-editor" onSubmit={submit}>
    <header className="editor-header"><div><div className="editor-kicker"><span>SIGNAL #{initial?.id || "NEW"}</span><span className="status-badge draft"><i />{initial?.lifecycle_status || "DRAFT"}</span></div><h1>{initial ? `${initial.symbol} ${initial.signal_type}` : "Create a signal"}</h1><p>Use verified stored levels only. No live broker prices are fetched here.</p></div><div className="header-actions"><a className="secondary-button" href="/admin/signals">Back to signals</a><button className="primary-button" disabled={busy || !editable}>{busy ? "Saving…" : "Save draft"}</button></div></header>
    <div className="editor-grid"><div className="editor-main">
      <section className="editor-card"><div className="card-heading"><div><h2>Market setup</h2><p>Prices use bounded decimal precision.</p></div></div>
        <div className="field-grid"><label>Symbol<input name="symbol" value={symbol} onChange={event => setSymbol(event.target.value.toUpperCase())} required maxLength={20} disabled={!editable} /></label><label>Market<input name="market" defaultValue={initial?.market || "FOREX"} required maxLength={30} disabled={!editable} /></label><label>Direction<select name="direction" value={direction} onChange={event => setDirection(event.target.value as "BUY" | "SELL")} disabled={!editable}><option>BUY</option><option>SELL</option></select></label><label>Timeframe<input name="timeframe" defaultValue={initial?.timeframe || "INTRADAY"} required maxLength={30} disabled={!editable} /></label></div>
        <div className="field-grid"><label>Entry type<select name="entry_type" defaultValue={initial?.entry_type || "MARKET"} disabled={!editable}><option>MARKET</option><option>LIMIT</option><option>STOP</option><option>RANGE</option></select></label><label>Entry price<input name="entry_price" type="number" step="0.000001" min="0" value={entry} onChange={event => setEntry(event.target.value)} required disabled={!editable} /></label><label>Range minimum<input name="entry_price_min" type="number" step="0.000001" defaultValue={value(initial?.entry_price_min)} disabled={!editable} /></label><label>Range maximum<input name="entry_price_max" type="number" step="0.000001" defaultValue={value(initial?.entry_price_max)} disabled={!editable} /></label></div>
        <div className="field-grid levels"><label>Stop loss<input type="number" step="0.000001" value={stop} onChange={event => setStop(event.target.value)} disabled={!editable} /></label>{targets.map((target, index) => <label key={index}>Target {index + 1}<input type="number" step="0.000001" value={target} onChange={event => setTargets(current => current.map((item, itemIndex) => itemIndex === index ? event.target.value : item))} disabled={!editable} /></label>)}</div>
      </section>
      <section className="editor-card"><div className="card-heading"><div><h2>Analysis</h2><p>Public detail content is optional for drafts and required summary before publishing.</p></div></div><label>Analysis summary<textarea rows={4} value={summary} onChange={event => setSummary(event.target.value)} maxLength={4000} disabled={!editable} /></label><label>Technical reasoning<textarea name="technical_reason" rows={7} defaultValue={value(initial?.technical_reason)} maxLength={10000} disabled={!editable} /></label><label>Astrology context<textarea name="astrology_reason" rows={5} defaultValue={value(initial?.astrology_reason)} maxLength={10000} disabled={!editable} /></label><label>Risk note<textarea name="risk_note" rows={4} defaultValue={value(initial?.risk_note)} maxLength={4000} disabled={!editable} /></label></section>
      <section className="editor-card signal-preview"><div className="card-heading"><div><h2>Public preview</h2><p>Preview only; no market values are synthesized.</p></div></div><article><div><strong>{symbol || "Symbol not set"}</strong><span className={`direction-chip ${direction.toLowerCase()}`}>{direction === "BUY" ? "↑ BUY" : "↓ SELL"}</span></div><dl><div><dt>Entry</dt><dd>{entry || "Not set"}</dd></div><div><dt>Stop loss</dt><dd>{stop || "Not set"}</dd></div><div><dt>Targets</dt><dd>{previewTargets}</dd></div></dl><p>{summary || "Add an analysis summary to complete the public preview."}</p></article></section>
    </div><aside className="editor-side"><section className="editor-card"><div className="card-heading"><div><h2>Publishing</h2></div></div><label>Publication<select name="publication_status" defaultValue={initial?.publication_status === "SCHEDULED" ? "SCHEDULED" : "DRAFT"} disabled={!editable}><option>DRAFT</option><option>SCHEDULED</option></select></label><label>Schedule time<input type="datetime-local" name="scheduled_at" defaultValue={initial?.scheduled_at?.slice(0,16) || ""} disabled={!editable} /></label><label>Expires at<input type="datetime-local" name="expires_at" defaultValue={initial?.expires_at?.slice(0,16) || ""} disabled={!editable} /></label><label>Risk level<select name="risk_level" defaultValue={initial?.risk_level || "MEDIUM"} disabled={!editable}><option>LOW</option><option>MEDIUM</option><option>HIGH</option></select></label><label>Confidence label<input name="confidence_label" defaultValue={value(initial?.confidence_label)} maxLength={60} placeholder="Descriptive label only" disabled={!editable} /></label><label className="toggle-label"><input name="featured" type="checkbox" defaultChecked={initial?.featured} disabled={!editable} /> Featured public signal</label>{message && <div className="form-error" role="alert">{message}</div>}<button className="primary-button" disabled={busy || !editable}>{busy ? "Saving…" : "Save draft"}</button>{!editable && <p className="support-note">Published and active signals are lifecycle-controlled. Duplicate one to create an editable draft.</p>}</section><section className="editor-card"><h2>Lifecycle</h2><p>Current state: <strong>{initial?.lifecycle_status || "DRAFT"}</strong></p><p>Publish and outcome changes use confirmed actions from the Signals list.</p></section></aside></div>
  </form>;
}
