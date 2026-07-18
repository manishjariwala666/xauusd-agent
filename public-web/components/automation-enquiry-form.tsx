"use client";

import { FormEvent, useState } from "react";

const services = ["AI Agents", "WhatsApp Automation", "Telegram Automation", "Email Automation", "CRM and Lead Automation", "Calendar and Booking", "Customer Support", "n8n Workflows", "Business Dashboards", "Custom API Integrations", "Website and Backend", "Social Publishing"];

export function AutomationEnquiryForm() {
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState(""); const [success, setSuccess] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setMessage(""); setSuccess(false);
    const form = event.currentTarget; const data = new FormData(form);
    const payload = Object.fromEntries(data.entries()) as Record<string, unknown>;
    payload.requested_services = data.getAll("requested_services"); payload.consent = data.has("consent");
    try {
      const csrf = await fetch("/api/automation-enquiries", { cache: "no-store" }).then((response) => response.json()) as { csrfToken?: string };
      const response = await fetch("/api/automation-enquiries", { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf.csrfToken || "" }, body: JSON.stringify(payload) });
      const result = await response.json() as { message?: string; detail?: string; reference?: string };
      if (!response.ok) setMessage(result.detail || result.message || "Please review the form and try again.");
      else { setSuccess(true); setMessage(`Thank you. Your enquiry reference is ${result.reference}.`); form.reset(); }
    } catch { setMessage("The enquiry service is temporarily unavailable. Please try again later."); }
    finally { setBusy(false); }
  }
  return <form className="automation-form" onSubmit={submit} aria-describedby="enquiry-status">
    <div className="form-grid"><label>Name<input name="name" required minLength={2} maxLength={120} autoComplete="name" /></label><label>Business email<input name="business_email" required type="email" maxLength={254} autoComplete="email" /></label><label>Company or brand<input name="company" maxLength={160} autoComplete="organization" /></label><label>Country<input name="country" required minLength={2} maxLength={100} autoComplete="country-name" /></label><label>Website URL<input name="website_url" type="url" pattern="https://.*" placeholder="https://" maxLength={2048} /></label><label>Phone / WhatsApp <span>Optional</span><input name="phone" type="tel" maxLength={40} autoComplete="tel" /></label><label>Business type<select name="business_type" required defaultValue=""><option value="" disabled>Select one</option>{["E-commerce","Real estate","Healthcare administration","Consulting","Financial research","Local services","Agency","Education","SaaS","Internal operations","Other"].map((item)=><option key={item}>{item}</option>)}</select></label><label>Budget range<select name="budget_range" required defaultValue=""><option value="" disabled>Request-based estimate</option>{["Under USD 2,500","USD 2,500–5,000","USD 5,000–15,000","USD 15,000+","Not decided"].map((item)=><option key={item}>{item}</option>)}</select></label><label>Preferred timeline<select name="preferred_timeline" required defaultValue=""><option value="" disabled>Select one</option>{["Within 1 month","1–3 months","3–6 months","Flexible / planning"].map((item)=><option key={item}>{item}</option>)}</select></label><label>Preferred contact<select name="preferred_contact_method" required defaultValue="EMAIL"><option value="EMAIL">Email</option><option value="PHONE">Phone</option><option value="WHATSAPP">WhatsApp</option></select></label></div>
    <fieldset><legend>Services needed</legend><div className="service-checks">{services.map((item)=><label key={item}><input type="checkbox" name="requested_services" value={item}/><span>{item}</span></label>)}</div></fieldset>
    <label>Current tools<textarea name="current_tools" rows={3} maxLength={1000} placeholder="CRM, inbox, calendar, spreadsheets or internal systems" /></label>
    <label>Project description<textarea name="project_description" required minLength={20} maxLength={5000} rows={6} /></label>
    <div className="form-grid"><label>Primary problem<textarea name="primary_problem" required minLength={10} maxLength={2000} rows={4} /></label><label>Expected outcome<textarea name="expected_outcome" required minLength={10} maxLength={2000} rows={4} /></label></div>
    <label className="honeypot" aria-hidden="true">Leave this empty<input name="website_confirm" tabIndex={-1} autoComplete="off" /></label>
    <label className="consent"><input name="consent" type="checkbox" required/><span>I consent to VenusRealm storing this information to review and respond to my project enquiry.</span></label>
    <button className="button button-gold" type="submit" disabled={busy}>{busy ? "Submitting…" : "Submit project enquiry"}</button>
    <div id="enquiry-status" className={`form-status ${success ? "success" : ""}`} role="status" aria-live="polite">{message}</div>
  </form>;
}
