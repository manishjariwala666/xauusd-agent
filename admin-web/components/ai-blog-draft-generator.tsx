"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

type ContentType = "complete_guide" | "news_analysis" | "how_to";

type ContentLength = "short" | "standard" | "long";

type Plan = {
  recommended_title: string;
  title_options: string[];
  focus_keyword: string;
  secondary_keywords: string[];
  search_intent: string;
  recommended_content_type: ContentType;
  recommended_length: ContentLength;
  outline: string[];
};

type DraftResponse = {
  id?: number;
  message?: string;
};

async function csrfToken(): Promise<string> {
  const response = await fetch("/api/admin/auth/csrf", {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("CSRF token unavailable");
  }

  const result = (await response.json()) as { csrfToken: string };
  return result.csrfToken;
}

export function AIBlogDraftGenerator() {
  const router = useRouter();
  const [mode, setMode] = useState<"article" | "pdf">("article");
  const [articleStep, setArticleStep] = useState<"inputs" | "review">("inputs");

  const [topic, setTopic] = useState("");
  const [keyword, setKeyword] = useState("");
  const [audience, setAudience] = useState("");
  const [location, setLocation] = useState("");

  const [plan, setPlan] = useState<Plan | null>(null);
  const [outline, setOutline] = useState<string[]>([]);
  const [selectedTitle, setSelectedTitle] = useState("");
  const [contentType, setContentType] =
    useState<ContentType>("complete_guide");
  const [contentLength, setContentLength] =
    useState<ContentLength>("standard");

  const [comparisonTable, setComparisonTable] = useState(true);
  const [faq, setFaq] = useState(true);
  const [schema, setSchema] = useState(true);
  const [internalLinks, setInternalLinks] = useState(true);
  const [riskDisclaimer, setRiskDisclaimer] = useState(true);

  const [busy, setBusy] = useState<"plan" | "draft" | null>(null);
  const [message, setMessage] = useState("");
  const [pdfFile, setPdfFile] = useState<File | null>(null);

  async function pdfBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = String(reader.result || "");
        resolve(result.includes(",") ? result.split(",", 2)[1] : result);
      };
      reader.onerror = () => reject(new Error("PDF could not be read."));
      reader.readAsDataURL(file);
    });
  }

  async function createPlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (busy || topic.trim().length < 3) {
      return;
    }

    setBusy("plan");
    setMessage("");
    try {
      const token = await csrfToken();

      const response = await fetch(
        "/api/admin/content/posts/plan-ai-draft",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": token,
          },
          body: JSON.stringify({
            topic: topic.trim(),
            target_keyword: keyword.trim(),
            target_audience: audience.trim(),
            location: location.trim(),
          }),
        }
      );

      const result = (await response.json()) as Plan & {
        message?: string;
      };

      if (!response.ok) {
        setMessage(result.message || "Article plan could not be created.");
        return;
      }

      setPlan(result);
      setOutline(result.outline || []);
      setArticleStep("review");
      setSelectedTitle(
        result.recommended_title ||
          result.title_options?.[0] ||
          topic.trim()
      );
      setKeyword(result.focus_keyword || keyword);
      setContentType(
        result.recommended_content_type || "complete_guide"
      );
      setContentLength(result.recommended_length || "standard");
    } catch {
      setMessage("AI planning service is temporarily unavailable.");
    } finally {
      setBusy(null);
    }
  }

  async function generateDraft() {
    if (!plan || busy || !selectedTitle.trim()) {
      return;
    }

    setBusy("draft");
    setMessage("");

    try {
      const token = await csrfToken();

      const response = await fetch(
        "/api/admin/content/posts/generate-ai-draft",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": token,
          },
          body: JSON.stringify({
            topic: topic.trim(),
            selected_title: selectedTitle.trim(),
            target_keyword: keyword.trim(),
            target_audience: audience.trim(),
            location: location.trim(),
            content_type: contentType,
            content_length: contentLength,
            include_comparison_table: comparisonTable,
            include_faq: faq,
            include_schema: schema,
            include_internal_links: internalLinks,
            include_risk_disclaimer: riskDisclaimer,
            outline: outline.map((item) => item.trim()).filter(Boolean),
            subcategory: "",
          }),
        }
      );

      const result = (await response.json()) as DraftResponse;

      if (!response.ok || !result.id) {
        setMessage(result.message || "Draft could not be generated.");
        return;
      }

      router.push(`/studio-v2?draft=${result.id}`);
      router.refresh();
    } catch {
      setMessage("AI generation service is temporarily unavailable.");
    } finally {
      setBusy(null);
    }
  }

  async function generatePdfDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!pdfFile || busy) return;
    if (pdfFile.type !== "application/pdf" || pdfFile.size > 5 * 1024 * 1024) {
      setMessage("Choose one PDF no larger than 5 MB.");
      return;
    }
    setBusy("draft");
    setMessage("");
    try {
      const [token, encoded] = await Promise.all([csrfToken(), pdfBase64(pdfFile)]);
      const response = await fetch("/api/admin/content/posts/generate-pdf-draft", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
        body: JSON.stringify({
          filename: pdfFile.name,
          pdf_base64: encoded,
          target_keyword: keyword.trim(),
          target_audience: audience.trim(),
          location: location.trim(),
          content_length: contentLength,
          include_comparison_table: comparisonTable,
          include_faq: faq,
          include_schema: schema,
          include_internal_links: internalLinks,
          include_risk_disclaimer: riskDisclaimer,
        }),
      });
      const result = (await response.json()) as DraftResponse;
      if (!response.ok || !result.id) {
        setMessage(result.message || "PDF draft could not be generated.");
        return;
      }
      router.push(`/studio-v2?draft=${result.id}`);
      router.refresh();
    } catch {
      setMessage("PDF processing service is temporarily unavailable.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="ai-writer">
      <nav className="ai-writer-tabs" aria-label="AI Content Studio mode">
        <button type="button" className={mode === "article" ? "active" : ""} onClick={() => { setMode("article"); setMessage(""); }}>Article planner</button>
        <button type="button" className={mode === "pdf" ? "active" : ""} onClick={() => { setMode("pdf"); setMessage(""); }}>PDF to draft</button>
      </nav>
      {mode === "article" ? (
      <form className="ai-writer-card" onSubmit={createPlan}>
        <header className="ai-writer-header">
          <div className="ai-writer-icon" aria-hidden="true">
            ✦
          </div>

          <div>
            <h2>Plan and generate a complete SEO article</h2>
            <p>
              First review title, keyword, article type, length and outline.
              A post is created only after final approval.
            </p>
          </div>
        </header>

        <div className="ai-writer-fields">
          <label className="ai-topic-field">
            Article topic *
            <textarea
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              rows={3}
              minLength={3}
              maxLength={500}
              required
              disabled={Boolean(busy)}
              placeholder="Example: XAUUSD scalping vs swing trading"
            />
          </label>

          <label>
            Focus keyword
            <input
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              maxLength={240}
              placeholder="Optional — AI will recommend one"
              disabled={Boolean(busy)}
            />
          </label>

          <label>
            Target audience
            <input
              value={audience}
              onChange={(event) => setAudience(event.target.value)}
              maxLength={240}
              placeholder="Example: beginner gold traders"
              disabled={Boolean(busy)}
            />
          </label>

          <label>
            GEO location
            <input
              aria-describedby="article-geo-help"
              value={location}
              onChange={(event) => setLocation(event.target.value)}
              maxLength={160}
              placeholder="Optional"
              disabled={Boolean(busy)}
            />
            <small id="article-geo-help" className="ai-field-help">
              Optional. Add a real city, region or country only when local
              search context genuinely matters.
            </small>
          </label>
        </div>

        {articleStep === "inputs" && (
          <footer className="ai-writer-footer">
            <div>
              <strong>Step 1 of 2 — Create article plan</strong>
              <small>No database post is created during planning.</small>
            </div>

            <button
              type="submit"
              className="primary-button ai-generate-button"
              disabled={Boolean(busy) || topic.trim().length < 3}
            >
              ✦{" "}
              {busy === "plan"
                ? "Creating plan…"
                : plan
                  ? "Update title and content plan"
                  : "Create title and content plan"}
            </button>
          </footer>
        )}

        {busy === "plan" && (
          <p className="ai-inline-status" role="status" aria-live="polite">
            <span className="ai-loading-spinner" aria-hidden="true" />
            Creating a review-only article plan. No post is being saved.
          </p>
        )}

        {plan && articleStep === "review" && (
          <section className="ai-plan-workbench">
            <header>
              <span>STEP 2 OF 2</span>
              <h3>Review and approve your article plan</h3>
            </header>

            <fieldset className="ai-title-options">
              <legend>Select a title</legend>

              {plan.title_options.map((title, index) => (
                <label key={`${index}-${title}`}>
                  <input
                    type="radio"
                    name="selected-title"
                    checked={selectedTitle === title}
                    onChange={() => setSelectedTitle(title)}
                    disabled={Boolean(busy)}
                  />

                  <span>
                    <small>Option {index + 1}</small>
                    <strong>{title}</strong>
                  </span>
                </label>
              ))}

              <label className="ai-custom-title">
                Custom selected title
                <input
                  value={selectedTitle}
                  onChange={(event) =>
                    setSelectedTitle(event.target.value)
                  }
                  maxLength={240}
                  disabled={Boolean(busy)}
                />
              </label>
            </fieldset>

            <div className="ai-plan-grid">
              <label>
                Content type
                <select
                  value={contentType}
                  onChange={(event) =>
                    setContentType(event.target.value as ContentType)
                  }
                  disabled={Boolean(busy)}
                >
                  <option value="complete_guide">Complete guide</option>
                  <option value="how_to">How-to guide</option>
                  <option value="news_analysis">News analysis</option>
                </select>
              </label>

              <label>
                Content length
                <select
                  value={contentLength}
                  onChange={(event) =>
                    setContentLength(
                      event.target.value as ContentLength
                    )
                  }
                  disabled={Boolean(busy)}
                >
                  <option value="short">Short · 700–900 words</option>
                  <option value="standard">
                    Standard · 1,200–1,600 words
                  </option>
                  <option value="long">
                    Long · 2,000–2,600 words
                  </option>
                </select>
              </label>

              <div className="ai-plan-summary">
                <small>Search intent</small>
                <strong>{plan.search_intent}</strong>
              </div>

              <div className="ai-plan-summary">
                <small>Recommended keyword</small>
                <strong>{keyword || plan.focus_keyword}</strong>
              </div>
            </div>

            <section className="ai-outline-preview">
              <h4>Edit article outline</h4>
              <p>
                One section per line. Reorder or rewrite headings before the
                draft is generated.
              </p>
              <textarea
                aria-label="Editable article outline"
                value={outline.join("\n")}
                onChange={(event) =>
                  setOutline(event.target.value.split("\n").slice(0, 20))
                }
                rows={Math.max(7, Math.min(outline.length + 1, 14))}
                maxLength={2_000}
                disabled={Boolean(busy)}
              />
            </section>

            <fieldset className="ai-writer-options">
              <legend>Include automatically</legend>

              <label>
                <input
                  type="checkbox"
                  checked={comparisonTable}
                  onChange={(event) =>
                    setComparisonTable(event.target.checked)
                  }
                />
                Real comparison table
              </label>

              <label>
                <input
                  type="checkbox"
                  checked={faq}
                  onChange={(event) => setFaq(event.target.checked)}
                />
                FAQ accordion
              </label>

              <label>
                <input
                  type="checkbox"
                  checked={schema}
                  onChange={(event) => setSchema(event.target.checked)}
                />
                Article + FAQ schema
              </label>

              <label>
                <input
                  type="checkbox"
                  checked={internalLinks}
                  onChange={(event) =>
                    setInternalLinks(event.target.checked)
                  }
                />
                Internal links
              </label>

              <label>
                <input
                  type="checkbox"
                  checked={riskDisclaimer}
                  onChange={(event) =>
                    setRiskDisclaimer(event.target.checked)
                  }
                />
                Risk disclaimer
              </label>
            </fieldset>

            <footer className="ai-plan-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setArticleStep("inputs")}
                disabled={Boolean(busy)}
              >
                ← Change inputs
              </button>

              <button
                type="button"
                className="primary-button ai-generate-button"
                onClick={generateDraft}
                disabled={Boolean(busy) || !selectedTitle.trim()}
              >
                ✦{" "}
                {busy === "draft"
                  ? "Generating approved draft…"
                  : "Approve plan and generate draft"}
              </button>
            </footer>
            {busy === "draft" && (
              <p className="ai-inline-status" role="status" aria-live="polite">
                <span className="ai-loading-spinner" aria-hidden="true" />
                Generating a draft for review. Publishing and image generation
                remain disabled.
              </p>
            )}
          </section>
        )}

        {message && (
          <p className="action-error ai-writer-message" role="alert">
            {message}
          </p>
        )}
      </form>
      ) : (
        <form className="ai-writer-card ai-pdf-card" onSubmit={generatePdfDraft}>
          <header className="ai-writer-header">
            <div className="ai-writer-icon" aria-hidden="true">PDF</div>
            <div><span>BOUNDED SOURCE WORKFLOW</span><h2>Create one summary-based draft from one PDF</h2><p>Maximum 5 MB and 20 pages. Missing facts remain marked verification required; the result is always a draft.</p></div>
          </header>
          <div className="ai-writer-fields">
            <label className="ai-topic-field">PDF source *<input type="file" accept="application/pdf,.pdf" required disabled={Boolean(busy)} onChange={(event) => setPdfFile(event.target.files?.[0] || null)} /></label>
            <label>Focus keyword<input value={keyword} onChange={(event) => setKeyword(event.target.value)} maxLength={240} disabled={Boolean(busy)} /></label>
            <label>Target audience<input value={audience} onChange={(event) => setAudience(event.target.value)} maxLength={240} disabled={Boolean(busy)} /></label>
            <label>GEO location<input aria-describedby="pdf-geo-help" value={location} onChange={(event) => setLocation(event.target.value)} maxLength={160} disabled={Boolean(busy)} /><small id="pdf-geo-help" className="ai-field-help">Optional. Use only when the source has genuine local relevance.</small></label>
            <label>Draft length<select value={contentLength} onChange={(event) => setContentLength(event.target.value as ContentLength)} disabled={Boolean(busy)}><option value="short">Short · 700–900 words</option><option value="standard">Standard · 1,200–1,600 words</option><option value="long">Long · 2,000–2,600 words</option></select></label>
          </div>
          <fieldset className="ai-writer-options">
            <legend>Include automatically</legend>
            <label><input type="checkbox" checked={comparisonTable} onChange={(event) => setComparisonTable(event.target.checked)} disabled={Boolean(busy)} />Real comparison table</label>
            <label><input type="checkbox" checked={faq} onChange={(event) => setFaq(event.target.checked)} disabled={Boolean(busy)} />FAQ accordion</label>
            <label><input type="checkbox" checked={schema} onChange={(event) => setSchema(event.target.checked)} disabled={Boolean(busy)} />Article + FAQ schema</label>
            <label><input type="checkbox" checked={internalLinks} onChange={(event) => setInternalLinks(event.target.checked)} disabled={Boolean(busy)} />Internal links</label>
            <label><input type="checkbox" checked={riskDisclaimer} onChange={(event) => setRiskDisclaimer(event.target.checked)} disabled={Boolean(busy)} />Risk disclaimer</label>
          </fieldset>
          <footer className="ai-writer-footer"><div><strong>One source → one draft</strong><small>No publishing, image generation or absent-fact invention.</small></div><button type="submit" className="primary-button" disabled={!pdfFile || Boolean(busy)}>{busy ? "Processing PDF…" : "Generate review draft"}</button></footer>
          {busy === "draft" && <p className="ai-inline-status" role="status" aria-live="polite"><span className="ai-loading-spinner" aria-hidden="true" />Reading the bounded PDF and creating one review draft. Nothing is published.</p>}
          {message && <p className="action-error ai-writer-message" role="alert">{message}</p>}
        </form>
      )}
    </section>
  );
}
