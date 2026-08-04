"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

type SeoHistoryCategorySnapshot = {
  id: string;
  label: string;
  score: number;
};

type SeoHistorySnapshot = {
  articleKey: string;
  savedAt: string;
  score: number;
  grade: string;
  categories: SeoHistoryCategorySnapshot[];
};

const SEO_HISTORY_STORAGE_KEY =
  "venusrealm-cms-v2-seo-history";

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

  const [seoHistory, setSeoHistory] = useState<
    SeoHistorySnapshot[]
  >([]);

  const articleHistoryKey =
    document.id !== null
      ? `id:${document.id}`
      : `slug:${document.slug.trim() || "untitled"}`;

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(
        SEO_HISTORY_STORAGE_KEY,
      );

      const parsed = raw
        ? JSON.parse(raw)
        : [];

      setSeoHistory(
        Array.isArray(parsed)
          ? parsed.filter(
              item =>
                item &&
                typeof item === "object" &&
                typeof item.articleKey === "string" &&
                typeof item.savedAt === "string" &&
                typeof item.score === "number",
            )
          : [],
      );
    } catch {
      setSeoHistory([]);
    }
  }, []);

  useEffect(() => {
    function handleSeoSnapshot() {
      const snapshot: SeoHistorySnapshot = {
        articleKey: articleHistoryKey,
        savedAt: new Date().toISOString(),
        score: analysis.advancedHealth.score,
        grade: analysis.advancedHealth.grade,
        categories:
          analysis.advancedHealth.categories.map(
            category => ({
              id: category.id,
              label: category.label,
              score: category.score,
            }),
          ),
      };

      setSeoHistory(current => {
        const articleSnapshots = current
          .filter(
            item =>
              item.articleKey === articleHistoryKey,
          )
          .concat(snapshot)
          .slice(-10);

        const next = [
          ...current.filter(
            item =>
              item.articleKey !== articleHistoryKey,
          ),
          ...articleSnapshots,
        ];

        window.localStorage.setItem(
          SEO_HISTORY_STORAGE_KEY,
          JSON.stringify(next),
        );

        return next;
      });
    }

    window.addEventListener(
      "venusrealm:seo-snapshot",
      handleSeoSnapshot,
    );

    return () => {
      window.removeEventListener(
        "venusrealm:seo-snapshot",
        handleSeoSnapshot,
      );
    };
  }, [
    analysis.advancedHealth.categories,
    analysis.advancedHealth.grade,
    analysis.advancedHealth.score,
    articleHistoryKey,
  ]);

  const articleHistory = useMemo(
    () =>
      seoHistory
        .filter(
          item =>
            item.articleKey === articleHistoryKey,
        )
        .sort(
          (left, right) =>
            new Date(left.savedAt).getTime() -
            new Date(right.savedAt).getTime(),
        ),
    [articleHistoryKey, seoHistory],
  );

  const previousSeoSnapshot =
    articleHistory.length > 1
      ? articleHistory[articleHistory.length - 2]
      : articleHistory[0] ?? null;

  const latestSeoSnapshot =
    articleHistory.length > 0
      ? articleHistory[articleHistory.length - 1]
      : null;

  const scoreComparisonBase =
    latestSeoSnapshot ?? previousSeoSnapshot;

  const scoreDelta =
    scoreComparisonBase
      ? analysis.advancedHealth.score -
        scoreComparisonBase.score
      : 0;

  const passedChecks = analysis.checks.filter(
    check => check.passed,
  ).length;

  const internalLinkSuggestions =
    buildInternalLinkSuggestions(
      document,
      drafts,
      analysis.links.records.map(link => link.url),
    );

  function handleQuickAction(target: string) {
    window.dispatchEvent(
      new CustomEvent("studio-seo-quick-action", {
        detail: { target },
      }),
    );
  }

  function safeReportFilename(): string {
    const base =
      document.slug.trim() ||
      document.title
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "") ||
      "untitled-article";

    return `${base}-seo-report`;
  }

  function triggerDownload(
    content: string,
    mimeType: string,
    extension: string,
  ) {
    const blob = new Blob([content], {
      type: `${mimeType};charset=utf-8`,
    });

    const url = URL.createObjectURL(blob);
    const link = window.document.createElement("a");

    link.href = url;
    link.download = `${safeReportFilename()}.${extension}`;

    window.document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
  }

  function buildSeoReport() {
    return {
      generatedAt: new Date().toISOString(),
      article: {
        id: document.id,
        title: document.title,
        slug: document.slug,
        status: document.status,
        excerpt: document.excerpt,
        canonicalUrl: document.seo.canonicalUrl,
        focusKeyword: document.seo.focusKeyword,
      },
      health: analysis.advancedHealth,
      seo: {
        score: analysis.seoScore,
        breakdown: analysis.scoreBreakdown,
      },
      content: {
        score: analysis.contentScore,
        wordCount: analysis.wordCount,
        readingTimeMinutes:
          analysis.readingTimeMinutes,
        checks: analysis.checks,
      },
      keyword: analysis.keywordAnalysis,
      readability: analysis.readability,
      publishChecklist: analysis.publishChecklist,
      imageSeo: analysis.imageSeo,
      schemaHealth: analysis.schemaHealth,
      socialPreview: analysis.socialPreview,
      links: analysis.links,
      internalLinkSuggestions,
    };
  }

  function downloadSeoReportJson() {
    triggerDownload(
      JSON.stringify(buildSeoReport(), null, 2),
      "application/json",
      "json",
    );
  }

  function csvCell(value: unknown): string {
    const normalized =
      value === null || value === undefined
        ? ""
        : typeof value === "object"
          ? JSON.stringify(value)
          : String(value);

    return `"${normalized.replace(/"/g, '""')}"`;
  }

  function downloadSeoReportCsv() {
    const rows: Array<[string, string, unknown]> = [
      ["Article", "Title", document.title],
      ["Article", "Slug", document.slug],
      ["Article", "Status", document.status],
      [
        "Article",
        "Canonical URL",
        document.seo.canonicalUrl,
      ],
      [
        "Article",
        "Focus Keyword",
        document.seo.focusKeyword,
      ],
      [
        "Overall Health",
        "Score",
        analysis.advancedHealth.score,
      ],
      [
        "Overall Health",
        "Grade",
        analysis.advancedHealth.grade,
      ],
      [
        "Overall Health",
        "Ready",
        analysis.advancedHealth.ready,
      ],
      ["SEO", "Score", analysis.seoScore],
      ["Content", "Score", analysis.contentScore],
      [
        "Readability",
        "Score",
        analysis.readability.score,
      ],
      ["Image SEO", "Score", analysis.imageSeo.score],
      [
        "Schema Health",
        "Score",
        analysis.schemaHealth.score,
      ],
      [
        "Social Preview",
        "Score",
        analysis.socialPreview.score,
      ],
      [
        "Publish Checklist",
        "Passed",
        `${analysis.publishChecklist.passed}/${analysis.publishChecklist.total}`,
      ],
      ["Links", "Total", analysis.links.total],
      ["Links", "Issues", analysis.links.issueCount],
    ];

    for (const category of analysis.advancedHealth.categories) {
      rows.push([
        "Category",
        category.label,
        category.score,
      ]);
    }

    for (const issue of analysis.advancedHealth.priorityIssues) {
      rows.push([
        `Priority Issue (${issue.severity})`,
        issue.label,
        `${issue.detail} [${issue.source}]`,
      ]);
    }

    for (const item of analysis.publishChecklist.items) {
      rows.push([
        "Publish Checklist",
        item.label,
        `${item.passed ? "PASS" : "FAIL"} - ${item.detail}`,
      ]);
    }

    const csv = [
      ["Section", "Metric", "Value"]
        .map(csvCell)
        .join(","),
      ...rows.map(row =>
        row.map(csvCell).join(","),
      ),
    ].join("\n");

    triggerDownload(
      `\uFEFF${csv}`,
      "text/csv",
      "csv",
    );
  }

  return (
    <aside className="studio-insights-panel">
      <section className="studio-insight-card studio-advanced-health-card">
        <header>
          <div>
            <span>ADVANCED SEO HEALTH</span>
            <h2>{analysis.advancedHealth.score}/100</h2>
          </div>

          <div className="studio-health-grade">
            <strong>{analysis.advancedHealth.grade}</strong>
            <small>{analysis.advancedHealth.label}</small>
          </div>
        </header>

        <div className="studio-seo-export-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={downloadSeoReportJson}
          >
            Export JSON
          </button>

          <button
            type="button"
            className="secondary-button"
            onClick={downloadSeoReportCsv}
          >
            Export CSV
          </button>
        </div>

        <div className="studio-health-status-row">
          <span
            className={
              analysis.advancedHealth.ready
                ? "health-ready"
                : "health-needs-work"
            }
          >
            {analysis.advancedHealth.ready
              ? "Publish ready"
              : "Needs work"}
          </span>

          <small>
            {analysis.advancedHealth.criticalCount} critical
            {" · "}
            {analysis.advancedHealth.warningCount} warnings
          </small>
        </div>

        <div className="studio-health-categories">
          {analysis.advancedHealth.categories.map(
            category => (
              <article
                key={category.id}
                className={`health-category-${category.status}`}
              >
                <header>
                  <strong>{category.label}</strong>
                  <span>{category.score}/100</span>
                </header>

                <div className="studio-health-progress">
                  <span
                    style={{
                      width: `${category.score}%`,
                    }}
                  />
                </div>

                <small>
                  Weight {category.weight}%
                </small>
              </article>
            ),
          )}
        </div>

        <div className="studio-health-priority">
          <h3>Priority Issues</h3>

          {analysis.advancedHealth.priorityIssues.length >
          0 ? (
            analysis.advancedHealth.priorityIssues.map(
              issue => (
                <article
                  key={issue.id}
                  className={
                    issue.severity === "critical"
                      ? "health-issue-critical"
                      : "health-issue-warning"
                  }
                >
                  <span>
                    {issue.severity === "critical"
                      ? "!"
                      : "⚠"}
                  </span>

                  <div>
                    <strong>{issue.label}</strong>
                    <small>{issue.detail}</small>
                    <em>{issue.source}</em>

                    <button
                      type="button"
                      className="studio-health-fix-button"
                      onClick={() =>
                        handleQuickAction(
                          issue.actionTarget,
                        )
                      }
                    >
                      Fix now
                    </button>
                  </div>
                </article>
              ),
            )
          ) : (
            <p>No priority SEO issues detected.</p>
          )}
        </div>
      </section>

      <section className="studio-insight-card studio-seo-history-card">
        <header>
          <div>
            <span>SEO HISTORY</span>
            <h2>
              {analysis.advancedHealth.score}/100
            </h2>
          </div>

          <strong
            className={
              scoreDelta > 0
                ? "seo-history-positive"
                : scoreDelta < 0
                  ? "seo-history-negative"
                  : "seo-history-neutral"
            }
          >
            {scoreComparisonBase
              ? scoreDelta > 0
                ? `+${scoreDelta}`
                : `${scoreDelta}`
              : "No history"}
          </strong>
        </header>

        <div className="studio-seo-history-summary">
          <div>
            <span>Previous score</span>
            <strong>
              {scoreComparisonBase
                ? `${scoreComparisonBase.score}/100`
                : "Not available"}
            </strong>
          </div>

          <div>
            <span>Current grade</span>
            <strong>
              {analysis.advancedHealth.grade}
            </strong>
          </div>

          <div>
            <span>Previous grade</span>
            <strong>
              {scoreComparisonBase?.grade ||
                "Not available"}
            </strong>
          </div>

          <div>
            <span>Snapshots</span>
            <strong>{articleHistory.length}/10</strong>
          </div>
        </div>

        {scoreComparisonBase ? (
          <div className="studio-seo-history-categories">
            {analysis.advancedHealth.categories.map(
              category => {
                const previousCategory =
                  scoreComparisonBase.categories.find(
                    item => item.id === category.id,
                  );

                const categoryDelta =
                  previousCategory
                    ? category.score -
                      previousCategory.score
                    : 0;

                return (
                  <article key={category.id}>
                    <div>
                      <strong>{category.label}</strong>
                      <small>
                        Previous{" "}
                        {previousCategory?.score ??
                          "N/A"}
                      </small>
                    </div>

                    <span>{category.score}</span>

                    <em
                      className={
                        categoryDelta > 0
                          ? "seo-history-positive"
                          : categoryDelta < 0
                            ? "seo-history-negative"
                            : "seo-history-neutral"
                      }
                    >
                      {categoryDelta > 0
                        ? `+${categoryDelta}`
                        : `${categoryDelta}`}
                    </em>
                  </article>
                );
              },
            )}
          </div>
        ) : (
          <p className="studio-seo-history-empty">
            Save this draft successfully to create the
            first SEO history snapshot.
          </p>
        )}

        {latestSeoSnapshot ? (
          <small className="studio-seo-history-date">
            Last saved snapshot:{" "}
            {new Date(
              latestSeoSnapshot.savedAt,
            ).toLocaleString()}
          </small>
        ) : null}
      </section>

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