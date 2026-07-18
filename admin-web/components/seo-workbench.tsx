"use client";
/* eslint-disable @next/next/no-img-element -- selected local/staging media may not use a configured image host */

import { useState } from "react";
import { SafeContentPreview } from "./safe-content-preview";
import type { Category, ContentDetail } from "@/lib/content-api";
import type { FaqEntry, SeoDetail, SeoIssue, SocialSeo } from "@/lib/seo-api";

type Tab = "preview" | "seo" | "og" | "twitter" | "structured" | "metadata";
type MediaItem = { id: number; public_url: string; thumbnail_url: string | null; original_filename: string; alt_text: string };
const tabs: Array<[Tab, string]> = [["preview", "Post Preview"], ["seo", "SEO Settings"], ["og", "Open Graph"], ["twitter", "X / Twitter"], ["structured", "FAQ / Schema"], ["metadata", "Content Metadata"]];
const dateTime = (value?: string | null) => value ? new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "Not set";
const csrf = async () => fetch("/api/admin/auth/csrf", { cache: "no-store" }).then(response => response.json()) as Promise<{ csrfToken: string }>;

export function SeoWorkbench({ initial, content, kind, categories, publicUrl }: { initial: SeoDetail | null; content: ContentDetail | null | undefined; kind: "posts" | "pages"; categories: Category[]; publicUrl: string }) {
  const [tab, setTab] = useState<Tab>("preview");
  const [title, setTitle] = useState(initial?.meta_title || "");
  const [description, setDescription] = useState(initial?.meta_description || "");
  const [keyword, setKeyword] = useState(initial?.focus_keyword || "");
  const [secondary, setSecondary] = useState((initial?.secondary_keywords || []).join(", "));
  const [canonical, setCanonical] = useState(initial?.canonical_url || "");
  const [index, setIndex] = useState(initial?.robots_index ?? true);
  const [follow, setFollow] = useState(initial?.robots_follow ?? true);
  const [sitemap, setSitemap] = useState(initial?.sitemap_included ?? false);
  const [og, setOg] = useState<SocialSeo>(initial?.open_graph || {});
  const [twitter, setTwitter] = useState<SocialSeo>({ card_type: "summary_large_image", ...(initial?.twitter_card || {}) });
  const [faq, setFaq] = useState<FaqEntry[]>([]);
  const [schema, setSchema] = useState("{}");
  const [structuredLoaded, setStructuredLoaded] = useState(false);
  const [issues, setIssues] = useState<SeoIssue[]>(initial?.seo_validation_issues || []);
  const [score, setScore] = useState(initial?.seo_score || 0);
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState("");

  async function openTab(next: Tab) {
    setTab(next);
    if (next !== "structured" || structuredLoaded || !content?.id) return;
    setBusy(true);
    try {
      const response = await fetch(`/api/admin/seo/${content.id}?include_structured=true`, { cache: "no-store" });
      const detail = await response.json() as SeoDetail;
      if (response.ok) { setFaq(detail.faq || []); setSchema(JSON.stringify(detail.schema_jsonld || {}, null, 2)); setStructuredLoaded(true); }
      else setMessage("Structured data could not be loaded.");
    } catch { setMessage("SEO service is temporarily unavailable."); } finally { setBusy(false); }
  }
  function payload() {
    let parsed: Record<string, unknown> | unknown[] | undefined;
    if (structuredLoaded) parsed = JSON.parse(schema || "{}");
    return { meta_title: title, meta_description: description, focus_keyword: keyword, secondary_keywords: secondary.split(",").map(item => item.trim()).filter(Boolean), canonical_url: canonical, robots_index: index, robots_follow: follow, sitemap_included: sitemap, open_graph: og, twitter_card: twitter, ...(structuredLoaded ? { faq, schema_jsonld: parsed } : {}) };
  }
  async function run(action: "validate" | "save") {
    if (!content?.id || busy) return; setBusy(true); setMessage("");
    try {
      const token = await csrf(); const response = await fetch(`/api/admin/seo/${content.id}${action === "validate" ? "/validate" : ""}`, { method: action === "validate" ? "POST" : "PUT", headers: { "Content-Type": "application/json", "X-CSRF-Token": token.csrfToken }, body: JSON.stringify(payload()) });
      const result = await response.json() as SeoDetail & { score?: number; issues?: SeoIssue[]; detail?: string; message?: string };
      if (!response.ok) { setMessage(result.detail || result.message || "SEO changes could not be processed."); return; }
      setScore(result.score ?? result.seo_score ?? score); setIssues(result.issues || result.seo_validation_issues || []); setMessage(action === "save" ? "SEO changes saved and audited." : "Validation completed without changing saved data.");
    } catch (error) { setMessage(error instanceof SyntaxError ? "Schema JSON-LD must contain valid JSON." : "SEO service is temporarily unavailable."); } finally { setBusy(false); }
  }
  function updateFaq(index: number, key: keyof FaqEntry, value: string) { setFaq(items => items.map((item, itemIndex) => itemIndex === index ? { ...item, [key]: value } : item)); }
  function moveFaq(index: number, direction: -1 | 1) { setFaq(items => { const target = index + direction; if (target < 0 || target >= items.length) return items; const copy = [...items]; [copy[index], copy[target]] = [copy[target], copy[index]]; return copy; }); }
  const previewTitle = title || content?.title || "SEO title preview"; const previewDescription = description || content?.excerpt || "Add a meta description to preview the search snippet.";

  return <section className="editor-card workbench" id="post-workbench" onChange={event => event.stopPropagation()}>
    <div className="tab-list" role="tablist" aria-label="SEO management panels">{tabs.map(([value, label]) => <button type="button" role="tab" aria-selected={tab === value} className={tab === value ? "active" : ""} onClick={() => openTab(value)} key={value}>{label}</button>)}</div>
    <div className="tab-panel" role="tabpanel">
      {!content?.id && <div className="readonly-notice"><strong>Save content before editing SEO</strong><span>The SEO record is securely linked after the post or page has an ID.</span></div>}
      {tab === "preview" && <div className="preview-stack"><SearchPreview title={previewTitle} url={canonical || publicUrl} description={previewDescription} /><div className="social-preview-grid"><SocialPreview network="Open Graph" social={og} fallback={{ title: previewTitle, description: previewDescription }} /><SocialPreview network="X / Twitter" social={twitter} fallback={og} /></div><ScoreSummary score={score} issues={issues} /><div className="content-preview-card"><div className="preview-label">Article preview <span>Sanitized</span></div><SafeContentPreview body={content?.body || ""} title={content?.title || ""} /></div></div>}
      {tab === "seo" && <div className="seo-form"><label>SEO title <Counter value={title} max={60} /><input value={title} onChange={event => setTitle(event.target.value)} maxLength={240} /></label><label>Meta description <Counter value={description} max={160} /><textarea value={description} onChange={event => setDescription(event.target.value)} rows={4} maxLength={500} /></label><div className="two-fields"><label>Focus keyword<input value={keyword} onChange={event => setKeyword(event.target.value)} maxLength={160} /></label><label>Secondary keywords<input value={secondary} onChange={event => setSecondary(event.target.value)} placeholder="gold, risk management" /></label></div><label>Slug<input value={content?.slug || ""} readOnly /><small className="support-note">Edit the slug in the Article section; uniqueness is validated here.</small></label><label>Canonical URL<input value={canonical} onChange={event => setCanonical(event.target.value)} placeholder="https://approved-site.example/path" inputMode="url" /></label><div className="seo-toggles"><label><input type="checkbox" checked={index} onChange={event => setIndex(event.target.checked)} /> Index</label><label><input type="checkbox" checked={follow} onChange={event => setFollow(event.target.checked)} /> Follow links</label><label><input type="checkbox" checked={sitemap} onChange={event => setSitemap(event.target.checked)} /> Include in sitemap</label></div><SeoActions busy={busy} disabled={!content?.id} onValidate={() => run("validate")} onSave={() => run("save")} /><ScoreSummary score={score} issues={issues} /></div>}
      {tab === "og" && <SocialEditor label="Open Graph" value={og} onChange={setOg} fallback={{ title: previewTitle, description: previewDescription }} />}
      {tab === "twitter" && <SocialEditor label="X / Twitter" value={twitter} onChange={setTwitter} fallback={og} twitter />}
      {tab === "structured" && <div className="schema-panel">{busy && !structuredLoaded ? <p>Loading structured data…</p> : <><div className="faq-editor"><div className="card-heading"><div><h2>FAQ entries</h2><p>Up to 20 safe question and answer pairs.</p></div><button type="button" className="secondary-button" onClick={() => setFaq(items => [...items, { question: "", answer: "" }])} disabled={faq.length >= 20}>Add FAQ</button></div>{faq.map((item, index) => <article className="faq-edit-row" key={index}><label>Question<input value={item.question} onChange={event => updateFaq(index, "question", event.target.value)} /></label><label>Answer<textarea rows={3} value={item.answer} onChange={event => updateFaq(index, "answer", event.target.value)} /></label><div><button type="button" onClick={() => moveFaq(index, -1)} disabled={!index}>↑</button><button type="button" onClick={() => moveFaq(index, 1)} disabled={index === faq.length - 1}>↓</button><button type="button" className="danger-link" onClick={() => setFaq(items => items.filter((_, itemIndex) => itemIndex !== index))}>Remove</button></div></article>)}</div><details><summary>Schema JSON-LD <span>Collapsed for performance</span></summary><div className="schema-editor"><textarea aria-label="Schema JSON-LD" rows={14} value={schema} onChange={event => setSchema(event.target.value)} spellCheck={false} /><button type="button" className="secondary-button" onClick={() => { try { setSchema(JSON.stringify(JSON.parse(schema), null, 2)); setMessage("Schema JSON formatted."); } catch { setMessage("Schema JSON-LD must contain valid JSON."); } }}>Format JSON</button></div></details><SeoActions busy={busy} disabled={!content?.id} onValidate={() => run("validate")} onSave={() => run("save")} /></>}</div>}
      {tab === "metadata" && <Metadata content={content} kind={kind} categories={categories} />}
      {message && <div className={message.includes("saved") || message.includes("completed") || message.includes("formatted") ? "media-message success" : "form-error"} role="status">{message}</div>}
    </div>
  </section>;
}

function Counter({ value, max }: { value: string; max: number }) { return <small className={value.length > max ? "counter over" : "counter"}>{value.length}/{max}</small>; }
function SeoActions({ busy, disabled, onValidate, onSave }: { busy: boolean; disabled: boolean; onValidate: () => void; onSave: () => void }) { return <div className="seo-actions"><button type="button" className="secondary-button" onClick={onValidate} disabled={busy || disabled}>Validate</button><button type="button" className="primary-button" onClick={onSave} disabled={busy || disabled}>{busy ? "Working…" : "Save SEO"}</button></div>; }
function SearchPreview({ title, url, description }: { title: string; url: string; description: string }) { return <div className="google-preview"><small>Google-style preview</small><a>{title}</a><span>{url}</span><p>{description}</p></div>; }
function ScoreSummary({ score, issues }: { score: number; issues: SeoIssue[] }) { return <div className="score-summary"><div className={`seo-score ${score >= 80 ? "good" : score >= 60 ? "fair" : ""}`}>{score}</div><div><strong>SEO score — no ranking guarantee</strong><p>{issues.length ? `${issues.length} validation issue${issues.length === 1 ? "" : "s"}` : "No deductions"}</p></div>{issues.length > 0 && <ul>{issues.map((issue, index) => <li key={`${issue.code}-${index}`} className={issue.severity}><b>{issue.points_lost ? `−${issue.points_lost}` : "Info"}</b> {issue.message}</li>)}</ul>}</div>; }
function SocialPreview({ network, social, fallback }: { network: string; social: SocialSeo; fallback: SocialSeo }) { return <article className="social-card-preview">{(social.image || fallback.image) ? <img src={social.image || fallback.image} alt={social.image_alt || ""} /> : <div className="social-image-empty">No image selected</div>}<small>{network}</small><strong>{social.title || fallback.title || "Social title"}</strong><p>{social.description || fallback.description || "Social description"}</p></article>; }
function SocialEditor({ label, value, onChange, fallback, twitter = false }: { label: string; value: SocialSeo; onChange: (value: SocialSeo) => void; fallback: SocialSeo; twitter?: boolean }) { return <div className="seo-form"><label>{label} title <Counter value={value.title || ""} max={60} /><input value={value.title || ""} onChange={event => onChange({ ...value, title: event.target.value })} placeholder={fallback.title || "Falls back to SEO title"} /></label><label>{label} description <Counter value={value.description || ""} max={200} /><textarea rows={4} value={value.description || ""} onChange={event => onChange({ ...value, description: event.target.value })} placeholder={fallback.description || "Falls back to meta description"} /></label>{twitter && <label>Card type<select value={value.card_type || "summary_large_image"} onChange={event => onChange({ ...value, card_type: event.target.value as SocialSeo["card_type"] })}><option value="summary_large_image">Large image summary</option><option value="summary">Summary</option></select></label>}<SeoImagePicker label={`${label} image`} value={value} onChange={onChange} /><SocialPreview network={label} social={value} fallback={fallback} /></div>; }
function SeoImagePicker({ label, value, onChange }: { label: string; value: SocialSeo; onChange: (value: SocialSeo) => void }) { const [open, setOpen] = useState(false); const [items, setItems] = useState<MediaItem[]>([]); const [search, setSearch] = useState(""); const [message, setMessage] = useState(""); async function load() { setOpen(true); const response = await fetch(`/api/admin/media?page_size=12&state=active&search=${encodeURIComponent(search)}`, { cache: "no-store" }); const result = await response.json() as { items?: MediaItem[]; message?: string }; if (response.ok) setItems(result.items || []); else setMessage(result.message || "Media could not be loaded."); } return <div className="seo-image-picker"><span className="field-label">{label}</span>{value.image ? <div className="selected-seo-image"><img src={value.image} alt={value.image_alt || ""} /><div><b>{value.image_alt ? "Alt text available" : "Alt text missing"}</b><button type="button" onClick={() => onChange({ ...value, image: "", media_id: null, image_alt: "" })}>Remove</button></div></div> : <div className="social-image-empty">Uses featured image fallback when available</div>}<div className="featured-controls"><button type="button" className="secondary-button" onClick={load}>{value.image ? "Replace from Media Library" : "Choose from Media Library"}</button></div>{open && <div className="media-picker"><div className="picker-search"><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search media" /><button type="button" onClick={load}>Search</button><button type="button" onClick={() => setOpen(false)}>Close</button></div><div className="picker-grid">{items.map(item => <button type="button" key={item.id} onClick={() => { onChange({ ...value, image: item.public_url, media_id: item.id, image_alt: item.alt_text }); setOpen(false); }}><img src={item.thumbnail_url || item.public_url} alt="" /><small>{item.original_filename}</small></button>)}</div>{message && <small>{message}</small>}</div>}</div>; }
function Metadata({ content, kind, categories }: { content: ContentDetail | null | undefined; kind: string; categories: Category[] }) { const category = categories.find(item => item.id === content?.category_id)?.title || content?.category || "Uncategorized"; const items = [["Content type", kind === "posts" ? "Blog post" : "Page"], ["Status", content?.status || "Draft"], ["Category", category], ["Subcategory", content?.subcategory || "—"], ["Author", content?.author || "Current administrator"], ["Views", String(content?.views || 0)], ["Publish date", dateTime(content?.published_at)], ["Updated date", dateTime(content?.updated_at)]]; return <div className="metadata-grid">{items.map(([label, value]) => <article key={label}><small>{label}</small><strong>{value}</strong></article>)}</div>; }
