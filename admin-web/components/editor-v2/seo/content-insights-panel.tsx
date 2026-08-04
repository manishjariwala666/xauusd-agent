"use client";

type InternalLinkDraft = {
  id: number;
  title: string;
  slug: string;
  status: string;
  updated_at: string | null;
};

type InternalLinkSuggestion = {
  id: number;
  title: string;
  url: string;
  anchorText: string;
  confidence: number;
  matchedTerms: string[];
};

const INTERNAL_LINK_STOP_WORDS = new Set([
  "a",
  "an",
  "and",
  "are",
  "as",
  "at",
  "be",
  "by",
  "for",
  "from",
  "how",
  "in",
  "is",
  "it",
  "of",
  "on",
  "or",
  "the",
  "to",
  "today",
  "what",
  "when",
  "why",
  "with",
]);

function internalLinkTokens(value: string): string[] {
  return Array.from(
    new Set(
      value
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, " ")
        .replace(/-/g, " ")
        .split(/\s+/)
        .map(token => token.trim())
        .filter(
          token =>
            token.length >= 3 &&
            !INTERNAL_LINK_STOP_WORDS.has(token),
        ),
    ),
  );
}

function buildInternalLinkSuggestions(
  document: CmsDocument,
  drafts: InternalLinkDraft[],
  linkedUrls: string[],
): InternalLinkSuggestion[] {
  const currentTokens = new Set(
    internalLinkTokens(
      [
        document.title,
        document.slug,
        document.excerpt,
        document.seo.focusKeyword,
      ].join(" "),
    ),
  );

  const normalizedLinkedUrls = new Set(
    linkedUrls.map(url =>
      url
        .trim()
        .toLowerCase()
        .replace(/^https?:\/\/(?:www\.)?venusrealm\.net/i, ""),
    ),
  );

  return drafts
    .filter(draft => draft.id !== document.id)
    .filter(draft => draft.slug.trim())
    .map(draft => {
      const url = `/blog/${draft.slug.trim()}`;
      const draftTokens = internalLinkTokens(
        `${draft.title} ${draft.slug}`,
      );

      const matchedTerms = draftTokens.filter(token =>
        currentTokens.has(token),
      );

      const overlapBase = Math.max(
        1,
        Math.min(currentTokens.size, draftTokens.length),
      );

      const confidence = Math.min(
        100,
        Math.round(
          (matchedTerms.length / overlapBase) * 100,
        ),
      );

      return {
        id: draft.id,
        title: draft.title || "Untitled article",
        url,
        anchorText:
          draft.title.trim() ||
          draft.slug.replace(/-/g, " "),
        confidence,
        matchedTerms,
      };
    })
    .filter(
      suggestion =>
        suggestion.matchedTerms.length > 0 &&
        !normalizedLinkedUrls.has(
          suggestion.url.toLowerCase(),
        ),
    )
    .sort(
      (left, right) =>
        right.confidence - left.confidence ||
        right.matchedTerms.length -
          left.matchedTerms.length ||
        left.title.localeCompare(right.title),
    )
    .slice(0, 5);
}

import {
  analyzeSeoDocument,
} from "@/lib/editor-v2/seo-analyzer";
import type {
  CmsDocument,
} from "@/lib/editor-v2/document-types";

export function ContentInsightsPanel({
  document,
  drafts,
}: {
  document: CmsDocument;
  drafts: InternalLinkDraft[];
}) {
  const analysis = analyzeSeoDocument(document);

  const passedChecks = analysis.checks.filter(
    check => check.passed,
  ).length;

  const internalLinkSuggestions =
    buildInternalLinkSuggestions(
      document,
      drafts,
      analysis.links.records.map(link => link.url),
    );

  return (
    <aside className="studio-insights-panel">
      <section className="studio-insight-card">
        <header>
          <div>
            <span>SEO SCORE</span>
            <h2>{analysis.seoScore}/100</h2>
          </div>

          <div
            className={`studio-score-badge ${
              analysis.seoScore >= 80
                ? "good"
                : analysis.seoScore >= 50
                  ? "warning"
                  : "poor"
            }`}
          >
            {analysis.seoScore >= 80
              ? "Good"
              : analysis.seoScore >= 50
                ? "Improve"
                : "Needs work"}
          </div>
        </header>

        <div className="studio-score-progress">
          <span
            style={{
              width: `${analysis.seoScore}%`,
            }}
          />
        </div>

        <ul>
          <li>H1: {analysis.headings.counts[1]}</li>
          <li>H2: {analysis.headings.counts[2]}</li>
          <li>H3: {analysis.headings.counts[3]}</li>
          <li>H4: {analysis.headings.counts[4]}</li>
          <li>H5: {analysis.headings.counts[5]}</li>
          <li>H6: {analysis.headings.counts[6]}</li>
          <li>Words: {analysis.wordCount}</li>
          <li>
            Reading time:{" "}
            {analysis.readingTimeMinutes} min
          </li>
        </ul>

        <div className="studio-score-breakdown">
          <h3>Score Breakdown</h3>

          {analysis.scoreBreakdown.map(item => (
            <div
              key={item.id}
              className="studio-score-row"
            >
              <span>{item.label}</span>

              <strong
                className={
                  item.passed
                    ? "score-good"
                    : "score-bad"
                }
              >
                +{item.earned}/{item.points}
              </strong>
            </div>
          ))}
        </div>

        <a
          href="/studio-v2/seo"
          className="secondary-button"
        >
          Open SEO Studio
        </a>
      </section>

      <section className="studio-insight-card">
        <header>
          <div>
            <span>CONTENT CHECKER</span>
            <h2>{analysis.contentScore}/100</h2>
          </div>

          <strong>
            {passedChecks}/{analysis.checks.length}
          </strong>
        </header>

        <div className="studio-content-check-list">
          {analysis.checks.map(check => (
            <article
              key={check.id}
              className={
                check.passed
                  ? "check-passed"
                  : "check-warning"
              }
            >
              <span>{check.passed ? "✓" : "!"}</span>

              <div>
                <strong>{check.label}</strong>
                <small>{check.detail}</small>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="studio-insight-card studio-keyword-card">
        <header>
          <div>
            <span>KEYWORD DENSITY</span>
            <h2>
              {analysis.keywordAnalysis.density}%
            </h2>
          </div>

          <strong>
            {analysis.keywordAnalysis.occurrences}{" "}
            matches
          </strong>
        </header>

        <div className="studio-keyword-grid">
          <div>
            <span>Keyword</span>
            <strong>
              {analysis.keywordAnalysis.keyword ||
                "Not set"}
            </strong>
          </div>

          <div>
            <span>Title</span>
            <strong>
              {analysis.keywordAnalysis.inTitle
                ? "✓"
                : "✗"}
            </strong>
          </div>

          <div>
            <span>Meta title</span>
            <strong>
              {analysis.keywordAnalysis.inMetaTitle
                ? "✓"
                : "✗"}
            </strong>
          </div>

          <div>
            <span>Meta description</span>
            <strong>
              {analysis.keywordAnalysis
                .inMetaDescription
                ? "✓"
                : "✗"}
            </strong>
          </div>

          <div>
            <span>Slug</span>
            <strong>
              {analysis.keywordAnalysis.inSlug
                ? "✓"
                : "✗"}
            </strong>
          </div>

          <div>
            <span>H1</span>
            <strong>
              {analysis.keywordAnalysis.inH1
                ? "✓"
                : "✗"}
            </strong>
          </div>

          <div>
            <span>H2 headings</span>
            <strong>
              {analysis.keywordAnalysis.h2Count}
            </strong>
          </div>

          <div>
            <span>H3 headings</span>
            <strong>
              {analysis.keywordAnalysis.h3Count}
            </strong>
          </div>
        </div>
      </section>

      <section className="studio-insight-card studio-readability-card">
        <header>
          <div>
            <span>READABILITY</span>
            <h2>{analysis.readability.score}/100</h2>
          </div>

          <strong>{analysis.readability.label}</strong>
        </header>

        <div className="studio-readability-grid">
          <div>
            <span>Sentences</span>
            <strong>
              {analysis.readability.sentenceCount}
            </strong>
          </div>

          <div>
            <span>Paragraphs</span>
            <strong>
              {analysis.readability.paragraphCount}
            </strong>
          </div>

          <div>
            <span>Avg. sentence</span>
            <strong>
              {analysis.readability
                .averageSentenceWords}{" "}
              words
            </strong>
          </div>

          <div>
            <span>Long sentences</span>
            <strong>
              {analysis.readability.longSentenceCount}
            </strong>
          </div>

          <div>
            <span>Long paragraphs</span>
            <strong>
              {analysis.readability.longParagraphCount}
            </strong>
          </div>
        </div>
      </section>

      <section className="studio-insight-card studio-publish-checklist-card">
        <header>
          <div>
            <span>PUBLISH CHECKLIST</span>
            <h2>
              {analysis.publishChecklist.passed}/
              {analysis.publishChecklist.total}
            </h2>
          </div>

          <strong>
            {analysis.publishChecklist.ready
              ? "Publish ready"
              : "Needs attention"}
          </strong>
        </header>

        <div className="studio-publish-checklist">
          {analysis.publishChecklist.items.map(item => (
            <article
              key={item.id}
              className={
                item.passed
                  ? "publish-check-passed"
                  : item.required
                    ? "publish-check-required"
                    : "publish-check-optional"
              }
            >
              <span>{item.passed ? "✓" : "!"}</span>

              <div>
                <strong>{item.label}</strong>
                <small>{item.detail}</small>
              </div>

              <em>
                {item.required
                  ? "Required"
                  : "Optional"}
              </em>
            </article>
          ))}
        </div>
      </section>

      <section className="studio-insight-card studio-image-seo-card">
        <header>
          <div>
            <span>IMAGE SEO</span>
            <h2>{analysis.imageSeo.score}/100</h2>
          </div>

          <strong>
            {analysis.imageSeo.total} images
          </strong>
        </header>

        <div className="studio-image-seo-grid">
          <div>
            <span>Missing ALT</span>
            <strong>
              {analysis.imageSeo.missingAlt}
            </strong>
          </div>

          <div>
            <span>Missing Source</span>
            <strong>
              {analysis.imageSeo.missingSource}
            </strong>
          </div>

          <div>
            <span>Missing Dimensions</span>
            <strong>
              {analysis.imageSeo.missingDimensions}
            </strong>
          </div>

          <div>
            <span>Missing Caption</span>
            <strong>
              {analysis.imageSeo.missingCaption}
            </strong>
          </div>

          <div>
            <span>External Images</span>
            <strong>
              {analysis.imageSeo.externalSources}
            </strong>
          </div>

          <div>
            <span>Large Images</span>
            <strong>
              {analysis.imageSeo.largeDimensions}
            </strong>
          </div>
        </div>

        {analysis.imageSeo.records.length > 0 ? (
          <div className="studio-image-records">
            {analysis.imageSeo.records.map(image => (
              <article
                key={image.id}
                className={
                  image.issues.length > 0
                    ? "image-has-issues"
                    : "image-clean"
                }
              >
                <header>
                  <strong>
                    {image.alt || "Missing ALT text"}
                  </strong>

                  <small>
                    {image.width && image.height
                      ? `${image.width} × ${image.height}`
                      : "Dimensions missing"}
                  </small>
                </header>

                <code title={image.src}>
                  {image.src || "Missing image source"}
                </code>

                {image.caption ? (
                  <p>{image.caption}</p>
                ) : null}

                {image.issues.length > 0 ? (
                  <ul>
                    {image.issues.map(issue => (
                      <li key={issue}>{issue}</li>
                    ))}
                  </ul>
                ) : (
                  <small className="studio-image-clean-message">
                    No image SEO issues detected
                  </small>
                )}
              </article>
            ))}
          </div>
        ) : (
          <p className="studio-image-empty">
            No image blocks detected in this article.
          </p>
        )}
      </section>

      <section className="studio-insight-card studio-internal-suggestions-card">
        <header>
          <div>
            <span>INTERNAL LINK SUGGESTIONS</span>
            <h2>{internalLinkSuggestions.length}</h2>
          </div>

          <strong>
            {internalLinkSuggestions.length > 0
              ? "Available"
              : "No matches"}
          </strong>
        </header>

        {internalLinkSuggestions.length > 0 ? (
          <div className="studio-internal-suggestions">
            {internalLinkSuggestions.map(suggestion => (
              <article key={suggestion.id}>
                <header>
                  <strong>{suggestion.title}</strong>

                  <span>
                    {suggestion.confidence}% match
                  </span>
                </header>

                <code>{suggestion.url}</code>

                <p>
                  Suggested anchor:{" "}
                  <strong>
                    {suggestion.anchorText}
                  </strong>
                </p>

                <small>
                  Matching terms:{" "}
                  {suggestion.matchedTerms.join(", ")}
                </small>
              </article>
            ))}
          </div>
        ) : (
          <p className="studio-internal-suggestions-empty">
            No relevant saved drafts found, or matching
            articles are already linked.
          </p>
        )}
      </section>

      <section className="studio-insight-card studio-schema-health-card">
        <header>
          <div>
            <span>SCHEMA HEALTH</span>
            <h2>{analysis.schemaHealth.score}/100</h2>
          </div>

          <strong>
            {analysis.schemaHealth.passed}/
            {analysis.schemaHealth.total}
          </strong>
        </header>

        <div className="studio-schema-health-summary">
          <div>
            <span>Schema</span>
            <strong>
              {analysis.schemaHealth.present
                ? "Present"
                : "Missing"}
            </strong>
          </div>

          <div>
            <span>Type</span>
            <strong>
              {analysis.schemaHealth.schemaType ||
                "Not set"}
            </strong>
          </div>

          <div>
            <span>Object</span>
            <strong>
              {analysis.schemaHealth.validObject
                ? "Valid"
                : "Invalid"}
            </strong>
          </div>
        </div>

        <div className="studio-schema-checks">
          {analysis.schemaHealth.checks.map(check => (
            <article
              key={check.id}
              className={
                check.passed
                  ? "schema-check-passed"
                  : check.required
                    ? "schema-check-required"
                    : "schema-check-optional"
              }
            >
              <span>{check.passed ? "✓" : "!"}</span>

              <div>
                <strong>{check.label}</strong>
                <small>{check.detail}</small>
              </div>

              <em>
                {check.required
                  ? "Required"
                  : "Recommended"}
              </em>
            </article>
          ))}
        </div>
      </section>

      <section className="studio-insight-card studio-social-preview-card">
        <header>
          <div>
            <span>SOCIAL PREVIEW</span>
            <h2>{analysis.socialPreview.score}/100</h2>
          </div>

          <strong>
            {analysis.socialPreview.passed}/
            {analysis.socialPreview.total}
          </strong>
        </header>

        <div className="studio-social-preview-card-box">
          {analysis.socialPreview.image ? (
            <img
              src={analysis.socialPreview.image}
              alt=""
            />
          ) : (
            <div className="studio-social-preview-image-empty">
              No preview image
            </div>
          )}

          <div>
            <small>venusrealm.net</small>

            <strong>
              {analysis.socialPreview.title ||
                "Untitled article"}
            </strong>

            <p>
              {analysis.socialPreview.description ||
                "Add a useful preview description."}
            </p>

            <code>
              {analysis.socialPreview.url ||
                "Preview URL unavailable"}
            </code>
          </div>
        </div>

        <div className="studio-social-platforms">
          {analysis.socialPreview.platforms.length > 0 ? (
            analysis.socialPreview.platforms.map(platform => (
              <span key={platform}>{platform}</span>
            ))
          ) : (
            <small>No platforms selected</small>
          )}
        </div>

        <div className="studio-social-preview-checks">
          {analysis.socialPreview.checks.map(check => (
            <article
              key={check.id}
              className={
                check.passed
                  ? "social-preview-check-passed"
                  : "social-preview-check-warning"
              }
            >
              <span>{check.passed ? "✓" : "!"}</span>

              <div>
                <strong>{check.label}</strong>
                <small>{check.detail}</small>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="studio-insight-card studio-link-audit-card">
        <header>
          <div>
            <span>LINK ANALYZER</span>
            <h2>{analysis.links.total}</h2>
          </div>

          <strong>
            {analysis.links.issueCount === 0
              ? "Clean"
              : `${analysis.links.issueCount} issues`}
          </strong>
        </header>

        <div className="studio-link-summary">
          <span>
            Internal{" "}
            <strong>
              {analysis.links.internal}
            </strong>
          </span>

          <span>
            External{" "}
            <strong>
              {analysis.links.external}
            </strong>
          </span>

          <span>
            Anchors{" "}
            <strong>
              {analysis.links.anchor}
            </strong>
          </span>

          <span>
            Invalid{" "}
            <strong>
              {analysis.links.invalid}
            </strong>
          </span>
        </div>

        {analysis.links.records.length > 0 ? (
          <div className="studio-link-records">
            {analysis.links.records.map(link => (
              <article
                key={link.id}
                className={
                  link.issues.length
                    ? "link-has-issues"
                    : "link-clean"
                }
              >
                <header>
                  <span
                    className={`link-kind link-kind-${link.kind}`}
                  >
                    {link.kind}
                  </span>

                  <small>{link.source}</small>
                </header>

                <strong>
                  {link.anchorText ||
                    "Missing anchor text"}
                </strong>

                <code title={link.url}>
                  {link.url || "Empty URL"}
                </code>

                <div className="studio-link-flags">
                  {link.nofollow ? (
                    <span>nofollow</span>
                  ) : null}

                  {link.sponsored ? (
                    <span>sponsored</span>
                  ) : null}

                  {link.ugc ? (
                    <span>ugc</span>
                  ) : null}

                  {link.targetBlank ? (
                    <span>new tab</span>
                  ) : null}
                </div>

                {link.issues.length > 0 ? (
                  <ul>
                    {link.issues.map(issue => (
                      <li key={issue}>
                        {issue
                          .replace(/-/g, " ")
                          .replace(
                            /^./,
                            value =>
                              value.toUpperCase(),
                          )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <small className="studio-link-clean-message">
                    No issues detected
                  </small>
                )}
              </article>
            ))}
          </div>
        ) : (
          <p className="studio-link-empty">
            No links detected in this article.
          </p>
        )}
      </section>

      <p className="studio-insights-note">
        Deterministic guidance hai. Search ranking
        ya trading outcome guarantee nahi hai.
      </p>
    </aside>
  );
}