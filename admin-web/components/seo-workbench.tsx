"use client";
/* eslint-disable @next/next/no-img-element -- selected local/staging media may not use a configured image host */

import { useEffect, useState } from "react";
import { SafeContentPreview } from "./safe-content-preview";
import type { Category, ContentDetail } from "@/lib/content-api";
import type { ContentAnalysis, FaqEntry, SeoDetail, SeoIssue, SocialSeo } from "@/lib/seo-api";

type Tab = "ai" | "preview" | "seo" | "content" | "og" | "twitter" | "structured" | "metadata";

type AiSuggestion = {
  saved: false;
  title_suggestions: string[];
  recommended_title: string;
  recommended_title_reason: string;
  seo_title: string;
  meta_description: string;
  focus_keyword: string;
  secondary_keywords: string[];
  slug: string;
  excerpt: string;
  image_alt: string;
  faq: FaqEntry[];
  improved_body: string;
  open_graph: SocialSeo;
  twitter_card: SocialSeo;
  schema_jsonld: Record<string, unknown>;
};
type MediaItem = { id: number; public_url: string; thumbnail_url: string | null; original_filename: string; alt_text: string };
const tabs: Array<[Tab, string]> = [["ai", "AI Assistant"], ["preview", "Post Preview"], ["seo", "SEO Settings"], ["content", "Content Checker"], ["og", "Open Graph"], ["twitter", "X / Twitter"], ["structured", "FAQ / Schema"], ["metadata", "Content Metadata"]];
const dateTime = (value?: string | null) => value ? new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "Not set";
const csrf = async () => fetch("/api/admin/auth/csrf", { cache: "no-store" }).then(response => response.json()) as Promise<{ csrfToken: string }>;

export function SeoWorkbench({
  initial,
  content,
  kind,
  categories,
  publicUrl,
  featuredImage,
  onScoreChange,
  onApplyArticle,
  onApplyImageAlt,
}: {
  initial: SeoDetail | null;
  content: ContentDetail | null | undefined;
  kind: "posts" | "pages";
  categories: Category[];
  publicUrl: string;
  featuredImage: { id: number | null; url: string | null; alt: string };
  onScoreChange?: (score: number) => void;
  onApplyArticle?: (change: {
    title?: string;
    slug?: string;
    excerpt?: string;
    body?: string;
  }) => void;
  onApplyImageAlt?: (alt: string) => void;
}) {
  const [tab, setTab] = useState<Tab>("preview");
  const [title, setTitle] = useState(initial?.meta_title || "");
  const [description, setDescription] = useState(initial?.meta_description || "");
  const [keyword, setKeyword] = useState(initial?.focus_keyword || "");
  const [secondary, setSecondary] = useState((initial?.secondary_keywords || []).join(", "));
  const [manualInternalLinks, setManualInternalLinks] = useState(
    (((initial as SeoDetail & { internal_links?: string[] })?.internal_links) || []).join(", "),
  );
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
  const [analysis, setAnalysis] = useState<ContentAnalysis | null>(null);
  const [aiSuggestion, setAiSuggestion] = useState<AiSuggestion | null>(null);
  const [aiTopic, setAiTopic] = useState(content?.title || "");
  const [aiAudience, setAiAudience] = useState("general");
  const [aiGoal, setAiGoal] = useState("educational");
  const [aiLanguage, setAiLanguage] = useState("English");
  const [aiRequest, setAiRequest] = useState<
    "complete_seo" | "titles" | "metadata" | "keywords" | "excerpt" | "faq" | "image_alt" | "improve_content"
  >("complete_seo");
  const [aiBusy, setAiBusy] = useState(false);
  const contentId = content?.id || 0;
  const contentTitle = content?.title || "";
  const contentSlug = content?.slug || "";
  const contentExcerpt = content?.excerpt || "";
  const contentBody = content?.body || "";
  const contentStatus = content?.status || "draft";

  useEffect(() => {
    if (!contentId) return;

    const timer = window.setTimeout(async () => {
      let parsedSchema: Record<string, unknown> = {};
      if (structuredLoaded) {
        try {
          const candidate = JSON.parse(schema || "{}");
          if (candidate && typeof candidate === "object" && !Array.isArray(candidate)) {
            parsedSchema = candidate as Record<string, unknown>;
          }
        } catch {
          parsedSchema = {};
        }
      }

      const markdownLinks = Array.from(
        contentBody.matchAll(/\[[^\]]+\]\(([^)]+)\)/g),
        match => match[1],
      ).filter(link => link.startsWith("/") || link.includes("venusrealm.net"));

      const inheritedTitle = title || contentTitle;
      const inheritedDescription = description || contentExcerpt;
      const inheritedImage = featuredImage.url || "";

      const livePayload = {
        title: contentTitle,
        slug: contentSlug,
        excerpt: contentExcerpt,
        body: contentBody,
        status: contentStatus,
        is_public: true,
        meta_title: title,
        meta_description: description,
        focus_keyword: keyword,
        secondary_keywords: secondary
          .split(",")
          .map(item => item.trim())
          .filter(Boolean),
        canonical_url: canonical,
        robots_index: index,
        robots_follow: follow,
        sitemap_included: sitemap,
        featured_image: inheritedImage,
        featured_media_id: featuredImage.id,
        featured_image_alt: featuredImage.alt,
        internal_links: Array.from(new Set([
          ...markdownLinks,
          ...manualInternalLinks
            .split(/[\n,]+/)
            .map(item => item.trim())
            .filter(Boolean),
        ])),
        open_graph: {
          ...og,
          title: og.title || inheritedTitle,
          description: og.description || inheritedDescription,
          image: og.image || inheritedImage,
          media_id: og.media_id || featuredImage.id,
          image_alt: og.image_alt || featuredImage.alt,
        },
        twitter_card: {
          ...twitter,
          card_type: twitter.card_type || "summary_large_image",
          title: twitter.title || og.title || inheritedTitle,
          description: twitter.description || og.description || inheritedDescription,
          image: twitter.image || og.image || inheritedImage,
          media_id: twitter.media_id || og.media_id || featuredImage.id,
          image_alt: twitter.image_alt || og.image_alt || featuredImage.alt,
        },
        faq: structuredLoaded ? faq : [],
        schema_jsonld: structuredLoaded ? parsedSchema : {},
      };

      try {
        const token = await csrf();
        const response = await fetch("/api/admin/content-studio/seo-preview", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": token.csrfToken,
          },
          body: JSON.stringify(livePayload),
        });

        const result = await response.json() as {
          score?: number;
          issues?: SeoIssue[];
        };

        if (!response.ok || typeof result.score !== "number") return;

        setScore(result.score);
        setIssues(result.issues || []);
        onScoreChange?.(result.score);
      } catch {
        // Keep the last reliable score when preview validation is unavailable.
      }
    }, 850);

    return () => window.clearTimeout(timer);
  }, [
    contentId,
    contentTitle,
    contentSlug,
    contentExcerpt,
    contentBody,
    contentStatus,
    title,
    description,
    keyword,
    secondary,
    manualInternalLinks,
    canonical,
    index,
    follow,
    sitemap,
    og,
    twitter,
    faq,
    schema,
    structuredLoaded,
    featuredImage.id,
    featuredImage.url,
    featuredImage.alt,
    onScoreChange,
  ]);

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
    return {
      meta_title: title,
      meta_description: description,
      focus_keyword: keyword,
      secondary_keywords: secondary.split(",").map(item => item.trim()).filter(Boolean),
      internal_links: manualInternalLinks
        .split(/[\n,]+/)
        .map(item => item.trim())
        .filter(Boolean),
      canonical_url: canonical,
      robots_index: index,
      robots_follow: follow,
      sitemap_included: sitemap,
      open_graph: og,
      twitter_card: twitter,
      ...(structuredLoaded ? { faq, schema_jsonld: parsed } : {}),
    };
  }
  async function run(action: "validate" | "save") {
    if (!content?.id || busy) return; setBusy(true); setMessage("");
    try {
      const token = await csrf(); const response = await fetch(`/api/admin/seo/${content.id}${action === "validate" ? "/validate" : ""}`, { method: action === "validate" ? "POST" : "PUT", headers: { "Content-Type": "application/json", "X-CSRF-Token": token.csrfToken }, body: JSON.stringify(payload()) });
      const result = await response.json() as SeoDetail & { score?: number; issues?: SeoIssue[]; detail?: string; message?: string };
      if (!response.ok) { setMessage(result.detail || result.message || "SEO changes could not be processed."); return; }
      const nextScore = result.score ?? result.seo_score ?? score;
      setScore(nextScore);
      onScoreChange?.(nextScore);
      setIssues(result.issues || result.seo_validation_issues || []);
      setMessage(action === "save" ? "SEO changes saved and audited." : "Validation completed without changing saved data.");
    } catch (error) { setMessage(error instanceof SyntaxError ? "Schema JSON-LD must contain valid JSON." : "SEO service is temporarily unavailable."); } finally { setBusy(false); }
  }
  async function generateAiSuggestions() {
    if (aiBusy) return;
    if (!aiTopic.trim()) {
      setMessage("Enter a topic or seed keyword first.");
      return;
    }
    setAiBusy(true);
    setMessage("");
    try {
      const token = await csrf();
      const response = await fetch("/api/admin/content-studio/ai-suggestions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": token.csrfToken,
        },
        body: JSON.stringify({
          request: aiRequest,
          topic: aiTopic.trim(),
          audience: aiAudience,
          content_goal: aiGoal,
          language: aiLanguage,
          title: content?.title || "",
          slug: content?.slug || "",
          excerpt: content?.excerpt || "",
          body: content?.body || "",
          focus_keyword: keyword,
          featured_image_alt: featuredImage.alt,
        }),
      });
      const result = await response.json() as AiSuggestion & {
        detail?: string;
        message?: string;
      };
      if (!response.ok) {
        setMessage(
          result.detail ||
          result.message ||
          "AI suggestions could not be generated.",
        );
        return;
      }
      setAiSuggestion(result);
      setMessage("AI suggestions generated. Review and apply only what you need.");
    } catch {
      setMessage("AI suggestion service is temporarily unavailable.");
    } finally {
      setAiBusy(false);
    }
  }

  function applySeoSuggestion() {
    if (!aiSuggestion) return;
    if (aiSuggestion.seo_title) setTitle(aiSuggestion.seo_title);
    if (aiSuggestion.meta_description) setDescription(aiSuggestion.meta_description);
    if (aiSuggestion.focus_keyword) setKeyword(aiSuggestion.focus_keyword);
    if (aiSuggestion.secondary_keywords.length) {
      setSecondary(aiSuggestion.secondary_keywords.join(", "));
    }
    if (aiSuggestion.open_graph) setOg(value => ({ ...value, ...aiSuggestion.open_graph }));
    if (aiSuggestion.twitter_card) {
      setTwitter(value => ({ ...value, ...aiSuggestion.twitter_card }));
    }
    if (aiSuggestion.faq.length) {
      setFaq(aiSuggestion.faq);
      setStructuredLoaded(true);
    }
    if (Object.keys(aiSuggestion.schema_jsonld || {}).length) {
      setSchema(JSON.stringify(aiSuggestion.schema_jsonld, null, 2));
      setStructuredLoaded(true);
    }
    setMessage("AI SEO suggestions applied locally. Save SEO after review.");
  }

  async function analyseContent() {
    if (!content?.id || busy) return;
    setBusy(true);
    setMessage("");
    try {
      const token = await csrf();
      const response = await fetch(`/api/admin/seo/${content.id}/analyse`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": token.csrfToken,
        },
        body: JSON.stringify({
          title: content.title || "",
          slug: content.slug || "",
          body: content.body || "",
          focus_keyword: keyword,
        }),
      });
      const result = await response.json() as ContentAnalysis & { detail?: string; message?: string };
      if (!response.ok) {
        setMessage(result.detail || result.message || "Content analysis could not be completed.");
        return;
      }
      setAnalysis(result);
      setMessage("Content analysis completed without changing saved data.");
    } catch {
      setMessage("Content analysis service is temporarily unavailable.");
    } finally {
      setBusy(false);
    }
  }

  function updateFaq(index: number, key: keyof FaqEntry, value: string) { setFaq(items => items.map((item, itemIndex) => itemIndex === index ? { ...item, [key]: value } : item)); }
  function moveFaq(index: number, direction: -1 | 1) { setFaq(items => { const target = index + direction; if (target < 0 || target >= items.length) return items; const copy = [...items]; [copy[index], copy[target]] = [copy[target], copy[index]]; return copy; }); }
  const previewTitle = title || content?.title || "SEO title preview"; const previewDescription = description || content?.excerpt || "Add a meta description to preview the search snippet.";

  return <section className="editor-card workbench" id="post-workbench" onChange={event => event.stopPropagation()}>
    <div className="tab-list" role="tablist" aria-label="SEO management panels">{tabs.map(([value, label]) => <button type="button" role="tab" aria-selected={tab === value} className={tab === value ? "active" : ""} onClick={() => openTab(value)} key={value}>{label}</button>)}</div>
    <div className="tab-panel" role="tabpanel">
      {!content?.id && <div className="readonly-notice"><strong>Save content before editing SEO</strong><span>The SEO record is securely linked after the post or page has an ID.</span></div>}
      {tab === "ai" && <div className="ai-assistant-panel">
        <div className="card-heading">
          <div>
            <h2>AI Content Assistant</h2>
            <p>Generate reviewable suggestions. Nothing is saved or published automatically.</p>
          </div>
        </div>

        <div className="ai-topic-grid">
          <label>
            Topic or seed keyword
            <input
              value={aiTopic}
              onChange={event => setAiTopic(event.target.value)}
              placeholder="Example: XAUUSD risk management"
              maxLength={500}
            />
          </label>

          <label>
            Audience
            <select value={aiAudience} onChange={event => setAiAudience(event.target.value)}>
              <option value="general">General readers</option>
              <option value="beginners">Beginners</option>
              <option value="experienced traders">Experienced traders</option>
              <option value="investors">Investors</option>
              <option value="business owners">Business owners</option>
            </select>
          </label>

          <label>
            Content goal
            <select value={aiGoal} onChange={event => setAiGoal(event.target.value)}>
              <option value="educational">Educational guide</option>
              <option value="news analysis">News analysis</option>
              <option value="evergreen SEO">Evergreen SEO article</option>
              <option value="thought leadership">Thought leadership</option>
              <option value="comparison">Comparison article</option>
            </select>
          </label>

          <label>
            Language
            <select value={aiLanguage} onChange={event => setAiLanguage(event.target.value)}>
              <option value="English">English</option>
              <option value="Hindi">Hindi</option>
              <option value="Hinglish">Hinglish</option>
              <option value="Gujarati">Gujarati</option>
            </select>
          </label>
        </div>

        <div className="ai-request-row">
          <label>
            AI task
            <select value={aiRequest} onChange={event => setAiRequest(event.target.value as typeof aiRequest)}>
              <option value="complete_seo">Complete SEO package</option>
              <option value="titles">Title suggestions</option>
              <option value="metadata">SEO title and description</option>
              <option value="keywords">Keyword suggestions</option>
              <option value="excerpt">Excerpt suggestion</option>
              <option value="faq">FAQ suggestions</option>
              <option value="image_alt">Image alt suggestion</option>
              <option value="improve_content">Improve article content</option>
            </select>
          </label>
          <button type="button" className="primary-button" onClick={generateAiSuggestions} disabled={aiBusy}>
            {aiBusy ? "Generating…" : "Generate AI Suggestions"}
          </button>
        </div>

        {aiSuggestion && <div className="ai-suggestion-stack">
          {aiSuggestion.recommended_title && <section className="ai-suggestion-card ai-recommended-title">
            <small>Recommended title</small>
            <h3>{aiSuggestion.recommended_title}</h3>
            {aiSuggestion.recommended_title_reason && <p>{aiSuggestion.recommended_title_reason}</p>}
            <div className="featured-controls">
              <button
                type="button"
                className="primary-button"
                onClick={() => onApplyArticle?.({ title: aiSuggestion.recommended_title })}
              >
                Apply recommended title
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={applySeoSuggestion}
              >
                Apply complete SEO
              </button>
            </div>
          </section>}

          {aiSuggestion.title_suggestions.length > 0 && <section className="ai-suggestion-card">
            <h3>Article title suggestions</h3>
            {aiSuggestion.title_suggestions.map(item => <div className="ai-suggestion-line" key={item}>
              <span>{item}</span>
              <button type="button" className="secondary-button" onClick={() => onApplyArticle?.({ title: item })}>Apply</button>
            </div>)}
          </section>}

          <section className="ai-suggestion-card">
            <h3>SEO package</h3>
            <p><strong>SEO title:</strong> {aiSuggestion.seo_title || "Not generated"}</p>
            <p><strong>Meta description:</strong> {aiSuggestion.meta_description || "Not generated"}</p>
            <p><strong>Focus keyword:</strong> {aiSuggestion.focus_keyword || "Not generated"}</p>
            <p><strong>Secondary keywords:</strong> {aiSuggestion.secondary_keywords.join(", ") || "Not generated"}</p>
            <button type="button" className="secondary-button" onClick={applySeoSuggestion}>Apply SEO package</button>
          </section>

          {(aiSuggestion.slug || aiSuggestion.excerpt) && <section className="ai-suggestion-card">
            <h3>Article details</h3>
            <p><strong>Slug:</strong> {aiSuggestion.slug || "Not generated"}</p>
            <p><strong>Excerpt:</strong> {aiSuggestion.excerpt || "Not generated"}</p>
            <button type="button" className="secondary-button" onClick={() => onApplyArticle?.({
              slug: aiSuggestion.slug || undefined,
              excerpt: aiSuggestion.excerpt || undefined,
            })}>Apply article details</button>
          </section>}

          {aiSuggestion.improved_body && <section className="ai-suggestion-card">
            <h3>Improved article</h3>
            <div className="ai-content-preview">{aiSuggestion.improved_body.replace(/<[^>]+>/g, " ").slice(0, 900)}</div>
            <button type="button" className="secondary-button" onClick={() => onApplyArticle?.({ body: aiSuggestion.improved_body })}>Replace article body</button>
          </section>}

          {aiSuggestion.image_alt && <section className="ai-suggestion-card">
            <h3>Featured-image alt</h3>
            <p>{aiSuggestion.image_alt}</p>
            <button type="button" className="secondary-button" onClick={() => onApplyImageAlt?.(aiSuggestion.image_alt)}>Apply image alt</button>
          </section>}

          {aiSuggestion.faq.length > 0 && <section className="ai-suggestion-card">
            <h3>FAQ suggestions</h3>
            {aiSuggestion.faq.map((item, index) => <details key={`${item.question}-${index}`}>
              <summary>{item.question}</summary>
              <p>{item.answer}</p>
            </details>)}
            <button type="button" className="secondary-button" onClick={applySeoSuggestion}>Apply FAQ and schema</button>
          </section>}
        </div>}
      </div>}
      {tab === "preview" && <div className="preview-stack"><SearchPreview title={previewTitle} url={canonical || publicUrl} description={previewDescription} /><div className="social-preview-grid"><SocialPreview network="Open Graph" social={og} fallback={{ title: previewTitle, description: previewDescription }} /><SocialPreview network="X / Twitter" social={twitter} fallback={og} /></div><ScoreSummary score={score} issues={issues} /><div className="content-preview-card"><div className="preview-label">Article preview <span>Sanitized</span></div><SafeContentPreview body={content?.body || ""} title={content?.title || ""} /></div></div>}
      {tab === "seo" && <div className="seo-form"><label>SEO title <Counter value={title} max={60} /><input value={title} onChange={event => setTitle(event.target.value)} maxLength={240} /></label><label>Meta description <Counter value={description} max={160} /><textarea value={description} onChange={event => setDescription(event.target.value)} rows={4} maxLength={500} /></label><div className="two-fields"><label>Focus keyword<input value={keyword} onChange={event => setKeyword(event.target.value)} maxLength={160} /></label><label>Secondary keywords<input value={secondary} onChange={event => setSecondary(event.target.value)} placeholder="gold, risk management" /></label></div><label>Internal links<textarea value={manualInternalLinks} onChange={event => setManualInternalLinks(event.target.value)} rows={3} placeholder="/blog&#10;/signals&#10;https://venusrealm.net/about" /><small className="support-note">One URL per line or comma-separated. Markdown links in the article are detected automatically.</small></label><label>Slug<input value={content?.slug || ""} readOnly /><small className="support-note">Edit the slug in the Article section; uniqueness is validated here.</small></label><label>Canonical URL<input value={canonical} onChange={event => setCanonical(event.target.value)} placeholder="https://approved-site.example/path" inputMode="url" /></label><div className="seo-toggles"><label><input type="checkbox" checked={index} onChange={event => setIndex(event.target.checked)} /> Index</label><label><input type="checkbox" checked={follow} onChange={event => setFollow(event.target.checked)} /> Follow links</label><label><input type="checkbox" checked={sitemap} onChange={event => setSitemap(event.target.checked)} /> Include in sitemap</label></div><SeoActions busy={busy} disabled={!content?.id} onValidate={() => run("validate")} onSave={() => run("save")} /><ScoreSummary score={score} issues={issues} /></div>}
      {tab === "content" && <ContentChecker analysis={analysis} busy={busy} disabled={!content?.id} onAnalyse={analyseContent} />}
      {tab === "og" && <SocialEditor label="Open Graph" value={og} onChange={setOg} fallback={{ title: previewTitle, description: previewDescription }} />}
      {tab === "twitter" && <SocialEditor label="X / Twitter" value={twitter} onChange={setTwitter} fallback={og} twitter />}
      {tab === "structured" && <div className="schema-panel">{busy && !structuredLoaded ? <p>Loading structured data…</p> : <><div className="faq-editor"><div className="card-heading"><div><h2>FAQ entries</h2><p>Up to 20 safe question and answer pairs.</p></div><button type="button" className="secondary-button" onClick={() => setFaq(items => [...items, { question: "", answer: "" }])} disabled={faq.length >= 20}>Add FAQ</button></div>{faq.map((item, index) => <article className="faq-edit-row" key={index}><label>Question<input value={item.question} onChange={event => updateFaq(index, "question", event.target.value)} /></label><label>Answer<textarea rows={3} value={item.answer} onChange={event => updateFaq(index, "answer", event.target.value)} /></label><div><button type="button" onClick={() => moveFaq(index, -1)} disabled={!index}>↑</button><button type="button" onClick={() => moveFaq(index, 1)} disabled={index === faq.length - 1}>↓</button><button type="button" className="danger-link" onClick={() => setFaq(items => items.filter((_, itemIndex) => itemIndex !== index))}>Remove</button></div></article>)}</div><details><summary>Schema JSON-LD <span>Collapsed for performance</span></summary><div className="schema-editor"><textarea aria-label="Schema JSON-LD" rows={14} value={schema} onChange={event => setSchema(event.target.value)} spellCheck={false} /><button type="button" className="secondary-button" onClick={() => { try { setSchema(JSON.stringify(JSON.parse(schema), null, 2)); setMessage("Schema JSON formatted."); } catch { setMessage("Schema JSON-LD must contain valid JSON."); } }}>Format JSON</button></div></details><SeoActions busy={busy} disabled={!content?.id} onValidate={() => run("validate")} onSave={() => run("save")} /></>}</div>}
      {tab === "metadata" && <Metadata content={content} kind={kind} categories={categories} />}
      {message && <div className={message.includes("saved") || message.includes("completed") || message.includes("formatted") ? "media-message success" : "form-error"} role="status">{message}</div>}
    </div>
  </section>;
}

function ContentChecker({ analysis, busy, disabled, onAnalyse }: {
  analysis: ContentAnalysis | null;
  busy: boolean;
  disabled: boolean;
  onAnalyse: () => void;
}) {
  if (!analysis) {
    return <div className="content-checker">
      <div className="card-heading">
        <div><h2>Content Checker</h2><p>Read-only quality and internal duplicate analysis.</p></div>
        <button type="button" className="primary-button" disabled={busy || disabled} onClick={onAnalyse}>
          {busy ? "Checking…" : "Run Content Checker"}
        </button>
      </div>
      <p className="support-note">Checks the current unsaved editor text. It does not publish or save content.</p>
    </div>;
  }

  const quality = analysis.quality;
  return <div className="content-checker">
    <div className="card-heading">
      <div><h2>Content Checker</h2><p>Internal database comparison only.</p></div>
      <button type="button" className="secondary-button" disabled={busy || disabled} onClick={onAnalyse}>
        {busy ? "Checking…" : "Check again"}
      </button>
    </div>

    <div className="metadata-grid">
      <article><small>Overall score</small><strong>{analysis.overall_score}/100</strong></article>
      <article><small>Content score</small><strong>{quality.score}/100</strong></article>
      <article><small>Originality</small><strong>{analysis.originality_score}/100</strong></article>
      <article><small>Duplicate risk</small><strong>{analysis.duplicates.risk}</strong></article>
      <article><small>Words</small><strong>{quality.word_count}</strong></article>
      <article><small>Reading time</small><strong>{quality.reading_time_minutes} min</strong></article>
      <article><small>Keyword density</small><strong>{quality.focus_keyword_density}%</strong></article>
      <article><small>Internal links</small><strong>{quality.internal_links}</strong></article>
      <article><small>External links</small><strong>{quality.external_links}</strong></article>
      <article><small>Missing image alt</small><strong>{quality.images_missing_alt}</strong></article>
    </div>

    <div className="two-fields">
      <section>
        <h3>Quality checks</h3>
        <ul className="analysis-check-list">
          {quality.checks.map(item => <li key={item.code} className={item.passed ? "passed" : "warning"}>
            <b>{item.passed ? "✓" : "!"}</b> {item.message}
          </li>)}
        </ul>
      </section>

      <section>
        <h3>Headings</h3>
        <div className="metadata-grid">
          {Object.entries(quality.headings).map(([heading, count]) =>
            <article key={heading}><small>{heading.toUpperCase()}</small><strong>{count}</strong></article>
          )}
        </div>
      </section>
    </div>

    <section>
      <h3>Closest internal matches</h3>
      {analysis.duplicates.matches.length === 0
        ? <p>No meaningful internal duplicate matches found.</p>
        : <div className="duplicate-match-list">
          {analysis.duplicates.matches.map(item => <article key={item.id}>
            <div><strong>{item.title || "Untitled content"}</strong><small>{item.status} · /{item.slug}</small></div>
            <b>{item.similarity}% similar</b>
            {item.exact_slug_match && <span className="status-badge">Exact slug match</span>}
          </article>)}
        </div>}
    </section>

    {quality.repeated_sentences.length > 0 && <section>
      <h3>Repeated text</h3>
      <ul>{quality.repeated_sentences.map((item, index) =>
        <li key={index}>{item.count}× — {item.text}</li>
      )}</ul>
    </section>}
  </div>;
}

function Counter({ value, max }: { value: string; max: number }) { return <small className={value.length > max ? "counter over" : "counter"}>{value.length}/{max}</small>; }
function SeoActions({ busy, disabled, onValidate, onSave }: { busy: boolean; disabled: boolean; onValidate: () => void; onSave: () => void }) { return <div className="seo-actions"><button type="button" className="secondary-button" onClick={onValidate} disabled={busy || disabled}>Validate</button><button type="button" className="primary-button" onClick={onSave} disabled={busy || disabled}>{busy ? "Working…" : "Save SEO"}</button></div>; }
function SearchPreview({ title, url, description }: { title: string; url: string; description: string }) { return <div className="google-preview"><small>Google-style preview</small><a>{title}</a><span>{url}</span><p>{description}</p></div>; }
function ScoreSummary({ score, issues }: { score: number; issues: SeoIssue[] }) { return <div className="score-summary"><div className={`seo-score ${score >= 80 ? "good" : score >= 60 ? "fair" : ""}`}>{score}</div><div><strong>SEO score — no ranking guarantee</strong><p>{issues.length ? `${issues.length} validation issue${issues.length === 1 ? "" : "s"}` : "No deductions"}</p></div>{issues.length > 0 && <ul>{issues.map((issue, index) => <li key={`${issue.code}-${index}`} className={issue.severity}><b>{issue.points_lost ? `−${issue.points_lost}` : "Info"}</b> {issue.message}</li>)}</ul>}</div>; }
function SocialPreview({ network, social, fallback }: { network: string; social: SocialSeo; fallback: SocialSeo }) { return <article className="social-card-preview">{(social.image || fallback.image) ? <img src={social.image || fallback.image} alt={social.image_alt || ""} /> : <div className="social-image-empty">No image selected</div>}<small>{network}</small><strong>{social.title || fallback.title || "Social title"}</strong><p>{social.description || fallback.description || "Social description"}</p></article>; }
function SocialEditor({ label, value, onChange, fallback, twitter = false }: { label: string; value: SocialSeo; onChange: (value: SocialSeo) => void; fallback: SocialSeo; twitter?: boolean }) { return <div className="seo-form"><label>{label} title <Counter value={value.title || ""} max={60} /><input value={value.title || ""} onChange={event => onChange({ ...value, title: event.target.value })} placeholder={fallback.title || "Falls back to SEO title"} /></label><label>{label} description <Counter value={value.description || ""} max={200} /><textarea rows={4} value={value.description || ""} onChange={event => onChange({ ...value, description: event.target.value })} placeholder={fallback.description || "Falls back to meta description"} /></label>{twitter && <label>Card type<select value={value.card_type || "summary_large_image"} onChange={event => onChange({ ...value, card_type: event.target.value as SocialSeo["card_type"] })}><option value="summary_large_image">Large image summary</option><option value="summary">Summary</option></select></label>}<SeoImagePicker label={`${label} image`} value={value} onChange={onChange} /><SocialPreview network={label} social={value} fallback={fallback} /></div>; }
function SeoImagePicker({ label, value, onChange }: { label: string; value: SocialSeo; onChange: (value: SocialSeo) => void }) { const [open, setOpen] = useState(false); const [items, setItems] = useState<MediaItem[]>([]); const [search, setSearch] = useState(""); const [message, setMessage] = useState(""); async function load() { setOpen(true); const response = await fetch(`/api/admin/media?page_size=12&state=active&search=${encodeURIComponent(search)}`, { cache: "no-store" }); const result = await response.json() as { items?: MediaItem[]; message?: string }; if (response.ok) setItems(result.items || []); else setMessage(result.message || "Media could not be loaded."); } return <div className="seo-image-picker"><span className="field-label">{label}</span>{value.image ? <div className="selected-seo-image"><img src={value.image} alt={value.image_alt || ""} /><div><b>{value.image_alt ? "Alt text available" : "Alt text missing"}</b><button type="button" onClick={() => onChange({ ...value, image: "", media_id: null, image_alt: "" })}>Remove</button></div></div> : <div className="social-image-empty">Uses featured image fallback when available</div>}<div className="featured-controls"><button type="button" className="secondary-button" onClick={load}>{value.image ? "Replace from Media Library" : "Choose from Media Library"}</button></div>{open && <div className="media-picker"><div className="picker-search"><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search media" /><button type="button" onClick={load}>Search</button><button type="button" onClick={() => setOpen(false)}>Close</button></div><div className="picker-grid">{items.map(item => <button type="button" key={item.id} onClick={() => { onChange({ ...value, image: item.public_url, media_id: item.id, image_alt: item.alt_text }); setOpen(false); }}><img src={item.thumbnail_url || item.public_url} alt="" /><small>{item.original_filename}</small></button>)}</div>{message && <small>{message}</small>}</div>}</div>; }
function Metadata({ content, kind, categories }: { content: ContentDetail | null | undefined; kind: string; categories: Category[] }) { const category = categories.find(item => item.id === content?.category_id)?.title || content?.category || "Uncategorized"; const items = [["Content type", kind === "posts" ? "Blog post" : "Page"], ["Status", content?.status || "Draft"], ["Category", category], ["Subcategory", content?.subcategory || "—"], ["Author", content?.author || "Current administrator"], ["Views", String(content?.views || 0)], ["Publish date", dateTime(content?.published_at)], ["Updated date", dateTime(content?.updated_at)]]; return <div className="metadata-grid">{items.map(([label, value]) => <article key={label}><small>{label}</small><strong>{value}</strong></article>)}</div>; }
