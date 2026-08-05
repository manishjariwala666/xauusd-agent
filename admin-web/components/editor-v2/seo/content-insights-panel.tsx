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
  MediaLibraryDialog,
  type MediaLibraryAsset,
} from "../../media-library-dialog";
import {
  analyzeSeoDocument,
} from "@/lib/editor-v2/seo-analyzer";
import type {
  CmsDocument,
} from "@/lib/editor-v2/document-types";

function FeaturedImageSidebarCard({
  document,
  onChange,
}: {
  document: CmsDocument;
  onChange: (
    mediaId: number | null,
    asset?: MediaLibraryAsset,
  ) => void;
}) {
  const [mediaOpen, setMediaOpen] = useState(false);
  const [selectedAsset, setSelectedAsset] =
    useState<MediaLibraryAsset | null>(null);
  const [imageFailed, setImageFailed] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadSelectedAsset() {
      if (!document.featuredMediaId) {
        setSelectedAsset(null);
        setImageFailed(false);
        return;
      }

      setLoading(true);

      try {
        const response = await fetch(
          `/api/admin/media/${document.featuredMediaId}`,
          {
            cache: "no-store",
            credentials: "same-origin",
          },
        );

        if (!response.ok) return;

        const asset =
          (await response.json()) as MediaLibraryAsset;

        if (!cancelled) {
          setSelectedAsset(asset);
          setImageFailed(false);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadSelectedAsset();

    return () => {
      cancelled = true;
    };
  }, [document.featuredMediaId]);

  function selectAsset(asset: MediaLibraryAsset) {
    setSelectedAsset(asset);
    setImageFailed(false);
    onChange(asset.id, asset);
  }

  function removeAsset() {
    setSelectedAsset(null);
    setImageFailed(false);
    onChange(null);
  }

  const previewUrl =
    selectedAsset?.thumbnail_url ||
    selectedAsset?.public_url ||
    "";

  return (
    <section className="studio-insight-card studio-featured-image-card">
      <header className="studio-featured-image-header">
        <h2>Featured image</h2>

        <span
          className="studio-featured-image-chevron"
          aria-hidden="true"
        >
         ⌃
        </span>
      </header>

      {loading ? (
        <div className="studio-featured-image-empty">
          Loading featured image…
        </div>
      ) : previewUrl && !imageFailed ? (
        <figure className="studio-featured-image-preview">
          <img
            src={previewUrl}
            alt={selectedAsset?.alt_text || ""}
            loading="lazy"
            decoding="async"
            onError={() => setImageFailed(true)}
          />

          <figcaption>
            {selectedAsset?.original_filename ||
              "Featured image"}
          </figcaption>
        </figure>
      ) : (
        <div className="studio-featured-image-empty">
          <span
            className="studio-featured-image-empty-icon"
            aria-hidden="true"
          >
            ▧
          </span>

          <strong>Set featured image</strong>
        </div>
      )}

      <div className="studio-featured-image-actions">
        <button
          type="button"
          className="secondary-button studio-featured-image-select"
          onClick={() => setMediaOpen(true)}
        >
          {document.featuredMediaId
            ? "Replace image"
            : "Select image"}
        </button>

        {document.featuredMediaId ? (
          <button
            type="button"
            className="text-button danger-link"
            onClick={removeAsset}
          >
            Remove
          </button>
        ) : null}
      </div>

      <MediaLibraryDialog
        open={mediaOpen}
        onClose={() => setMediaOpen(false)}
        onSelect={selectAsset}
      />
    </section>
  );
}

export function ContentInsightsPanel({
  document,
  drafts,
  onFeaturedMediaChange,
}: {
  document: CmsDocument;
  drafts: InternalLinkDraft[];
  onFeaturedMediaChange: (
    mediaId: number | null,
    asset?: MediaLibraryAsset,
  ) => void;
}) {
  const analysis = analyzeSeoDocument(document);

  const [seoHistory, setSeoHistory] = useState<
    SeoHistorySnapshot[]
  >([]);

  const [selectedSnapshotA, setSelectedSnapshotA] =
    useState<string>("");

  const [selectedSnapshotB, setSelectedSnapshotB] =
    useState<string>("");

  const [selectedTrendCategory, setSelectedTrendCategory] =
    useState<string>("overall");

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

  const snapshotA =
    articleHistory.find(
      item => item.savedAt === selectedSnapshotA,
    ) ?? null;

  const snapshotB =
    articleHistory.find(
      item => item.savedAt === selectedSnapshotB,
    ) ?? null;

  const selectedScoreDelta =
    snapshotA && snapshotB
      ? snapshotB.score - snapshotA.score
      : null;

  function persistSeoHistory(
    next: SeoHistorySnapshot[],
  ) {
    window.localStorage.setItem(
      SEO_HISTORY_STORAGE_KEY,
      JSON.stringify(next),
    );

    setSeoHistory(next);
  }

  function clearCurrentArticleHistory() {
    if (articleHistory.length === 0) return;

    const confirmed = window.confirm(
      "Clear SEO history for this article only?",
    );

    if (!confirmed) return;

    const next = seoHistory.filter(
      item => item.articleKey !== articleHistoryKey,
    );

    persistSeoHistory(next);
    setSelectedSnapshotA("");
    setSelectedSnapshotB("");
  }

  function clearAllSeoHistory() {
    if (seoHistory.length === 0) return;

    const confirmed = window.confirm(
      "Clear all locally stored SEO history?",
    );

    if (!confirmed) return;

    window.localStorage.removeItem(
      SEO_HISTORY_STORAGE_KEY,
    );

    setSeoHistory([]);
    setSelectedSnapshotA("");
    setSelectedSnapshotB("");
  }

  function exportSeoTrendJson() {
    triggerDownload(
      JSON.stringify(
        {
          version: 1,
          exportedAt: new Date().toISOString(),
          articleKey: articleHistoryKey,
          snapshots: articleHistory,
        },
        null,
        2,
      ),
      "application/json",
      "trend.json",
    );
  }

  function exportSeoTrendCsv() {
    const rows: Array<Record<string, string | number>> =
      articleHistory.map(snapshot => {
        const categoryValues =
          snapshot.categories.reduce<Record<string, number>>(
            (result, category) => {
              result[category.label] = category.score;
              return result;
            },
            {},
          );

        return {
          savedAt: snapshot.savedAt,
          score: snapshot.score,
          grade: snapshot.grade,
          ...categoryValues,
        };
      });

    const categoryLabels = Array.from(
      new Set(
        articleHistory.flatMap(snapshot =>
          snapshot.categories.map(
            category => category.label,
          ),
        ),
      ),
    );

    const headers = [
      "Saved At",
      "Overall Score",
      "Grade",
      ...categoryLabels,
    ];

    const csvRows = [
      headers.map(csvCell).join(","),
      ...rows.map(row =>
        [
          row.savedAt,
          row.score,
          row.grade,
          ...categoryLabels.map(
            label => row[label] ?? "",
          ),
        ]
          .map(csvCell)
          .join(","),
      ),
    ];

    triggerDownload(
      `\uFEFF${csvRows.join("\n")}`,
      "text/csv",
      "trend.csv",
    );
  }

  function backupAllSeoHistory() {
    triggerDownload(
      JSON.stringify(
        {
          version: 1,
          exportedAt: new Date().toISOString(),
          snapshots: seoHistory,
        },
        null,
        2,
      ),
      "application/json",
      "history-backup.json",
    );
  }

  async function restoreSeoHistoryBackup(
    file: File,
  ) {
    let parsed: unknown;

    try {
      parsed = JSON.parse(await file.text());
    } catch {
      window.alert("Invalid JSON backup file.");
      return;
    }

    if (
      !parsed ||
      typeof parsed !== "object" ||
      !("version" in parsed) ||
      !("snapshots" in parsed)
    ) {
      window.alert("Invalid SEO history backup format.");
      return;
    }

    const backup = parsed as {
      version?: unknown;
      snapshots?: unknown;
    };

    if (
      backup.version !== 1 ||
      !Array.isArray(backup.snapshots)
    ) {
      window.alert("Unsupported SEO history backup.");
      return;
    }

    const validSnapshots =
      backup.snapshots.filter(
        (item): item is SeoHistorySnapshot =>
          Boolean(
            item &&
            typeof item === "object" &&
            "articleKey" in item &&
            typeof item.articleKey === "string" &&
            "savedAt" in item &&
            typeof item.savedAt === "string" &&
            "score" in item &&
            typeof item.score === "number" &&
            "grade" in item &&
            typeof item.grade === "string" &&
            "categories" in item &&
            Array.isArray(item.categories),
          ),
      );

    if (validSnapshots.length === 0) {
      window.alert("Backup contains no valid snapshots.");
      return;
    }

    const confirmed = window.confirm(
      `Restore ${validSnapshots.length} snapshots and overwrite current local SEO history?`,
    );

    if (!confirmed) return;

    persistSeoHistory(validSnapshots);
    setSelectedSnapshotA("");
    setSelectedSnapshotB("");

    window.alert("SEO history restored successfully.");
  }

  const trendPoints = articleHistory.map(
    snapshot => ({
      label: new Date(
        snapshot.savedAt,
      ).toLocaleDateString(),
      score:
        selectedTrendCategory === "overall"
          ? snapshot.score
          : (
              snapshot.categories.find(
                item =>
                  item.id === selectedTrendCategory,
              )?.score ?? 0
            ),
    }),
  );

  const trendMax =
    trendPoints.length > 0
      ? Math.max(
          ...trendPoints.map(point => point.score),
        )
      : 100;

  const trendMin =
    trendPoints.length > 0
      ? Math.min(
          ...trendPoints.map(point => point.score),
        )
      : 0;

  const trendRange =
    Math.max(1, trendMax - trendMin);

  const trendPolyline =
    trendPoints
      .map((point, index) => {
        const x =
          trendPoints.length === 1
            ? 150
            : (index * 300) /
              (trendPoints.length - 1);

        const y =
          120 -
          ((point.score - trendMin) /
            trendRange) *
            100;

        return `${x},${y}`;
      })
      .join(" ");

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

  function printSeoReport() {
    window.print();
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
    <>
      <section className="studio-seo-print-report">
        <header>
          <div>
            <span>VENUSREALM SEO AUDIT REPORT</span>
            <h1>
              {document.title ||
                "Untitled VenusRealm article"}
            </h1>
          </div>

          <strong>
            {analysis.advancedHealth.grade}
          </strong>
        </header>

        <div className="studio-seo-print-meta">
          <div>
            <span>Generated</span>
            <strong>
              {new Date().toLocaleString()}
            </strong>
          </div>

          <div>
            <span>Status</span>
            <strong>{document.status}</strong>
          </div>

          <div>
            <span>Slug</span>
            <strong>
              {document.slug || "Not set"}
            </strong>
          </div>

          <div>
            <span>Focus keyword</span>
            <strong>
              {document.seo.focusKeyword ||
                "Not set"}
            </strong>
          </div>
        </div>

        <section>
          <h2>Overall SEO Health</h2>

          <div className="studio-seo-print-score">
            <strong>
              {analysis.advancedHealth.score}/100
            </strong>

            <span>
              {analysis.advancedHealth.label}
            </span>

            <small>
              {analysis.advancedHealth.criticalCount}
              {" critical · "}
              {analysis.advancedHealth.warningCount}
              {" warnings"}
            </small>
          </div>
        </section>

        <section>
          <h2>Category Scores</h2>

          <div className="studio-seo-print-grid">
            {analysis.advancedHealth.categories.map(
              category => (
                <article key={category.id}>
                  <span>{category.label}</span>
                  <strong>
                    {category.score}/100
                  </strong>
                  <small>
                    Weight {category.weight}%
                  </small>
                </article>
              ),
            )}
          </div>
        </section>

        <section>
          <h2>Priority Issues</h2>

          {analysis.advancedHealth.priorityIssues.length >
          0 ? (
            <div className="studio-seo-print-list">
              {analysis.advancedHealth.priorityIssues.map(
                issue => (
                  <article key={issue.id}>
                    <strong>{issue.label}</strong>
                    <p>{issue.detail}</p>
                    <small>
                      {issue.source}
                      {" · "}
                      {issue.severity}
                    </small>
                  </article>
                ),
              )}
            </div>
          ) : (
            <p>No priority SEO issues detected.</p>
          )}
        </section>

        <section>
          <h2>Publish Checklist</h2>

          <div className="studio-seo-print-list">
            {analysis.publishChecklist.items.map(
              item => (
                <article key={item.id}>
                  <strong>
                    {item.passed ? "PASS" : "FAIL"}
                    {" — "}
                    {item.label}
                  </strong>
                  <p>{item.detail}</p>
                  <small>
                    {item.required
                      ? "Required"
                      : "Optional"}
                  </small>
                </article>
              ),
            )}
          </div>
        </section>

        <section>
          <h2>Technical Summary</h2>

          <div className="studio-seo-print-grid">
            <article>
              <span>SEO score</span>
              <strong>
                {analysis.seoScore}/100
              </strong>
            </article>

            <article>
              <span>Content score</span>
              <strong>
                {analysis.contentScore}/100
              </strong>
            </article>

            <article>
              <span>Readability</span>
              <strong>
                {analysis.readability.score}/100
              </strong>
            </article>

            <article>
              <span>Image SEO</span>
              <strong>
                {analysis.imageSeo.score}/100
              </strong>
            </article>

            <article>
              <span>Schema health</span>
              <strong>
                {analysis.schemaHealth.score}/100
              </strong>
            </article>

            <article>
              <span>Social preview</span>
              <strong>
                {analysis.socialPreview.score}/100
              </strong>
            </article>

            <article>
              <span>Word count</span>
              <strong>{analysis.wordCount}</strong>
            </article>

            <article>
              <span>Link issues</span>
              <strong>
                {analysis.links.issueCount}
              </strong>
            </article>
          </div>
        </section>

        <footer>
          Deterministic SEO audit. Search ranking
          guarantee nahi hai.
        </footer>
      </section>

      <aside className="studio-insights-panel">
        <FeaturedImageSidebarCard
          document={document}
          onChange={onFeaturedMediaChange}
        />

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

          <button
            type="button"
            className="secondary-button"
            onClick={printSeoReport}
          >
            Print / Save PDF
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

        <div className="studio-seo-trend-chart">
          <header>
            <div>
              <strong>Score Trend</strong>
              <small>
                Last {articleHistory.length} snapshots
              </small>
            </div>

            <select
              value={selectedTrendCategory}
              onChange={event =>
                setSelectedTrendCategory(
                  event.target.value,
                )
              }
            >
              <option value="overall">
                Overall health
              </option>

              {analysis.advancedHealth.categories.map(
                category => (
                  <option
                    key={category.id}
                    value={category.id}
                  >
                    {category.label}
                  </option>
                ),
              )}
            </select>
          </header>

          {trendPoints.length > 0 ? (
            <>
              <div className="studio-seo-trend-stats">
                <div>
                  <span>Highest</span>
                  <strong>{trendMax}</strong>
                </div>

                <div>
                  <span>Lowest</span>
                  <strong>{trendMin}</strong>
                </div>

                <div>
                  <span>Change</span>
                  <strong
                    className={
                      trendPoints.length > 1 &&
                      trendPoints[
                        trendPoints.length - 1
                      ].score >
                        trendPoints[0].score
                        ? "seo-history-positive"
                        : trendPoints.length > 1 &&
                            trendPoints[
                              trendPoints.length - 1
                            ].score <
                              trendPoints[0].score
                          ? "seo-history-negative"
                          : "seo-history-neutral"
                    }
                  >
                    {trendPoints.length > 1
                      ? trendPoints[
                          trendPoints.length - 1
                        ].score -
                          trendPoints[0].score >
                        0
                        ? `+${
                            trendPoints[
                              trendPoints.length - 1
                            ].score -
                            trendPoints[0].score
                          }`
                        : `${
                            trendPoints[
                              trendPoints.length - 1
                            ].score -
                            trendPoints[0].score
                          }`
                      : "0"}
                  </strong>
                </div>
              </div>

              <div className="studio-seo-trend-svg-wrap">
                <svg
                  viewBox="0 0 300 140"
                  role="img"
                  aria-label="SEO score trend chart"
                  preserveAspectRatio="none"
                >
                  <line
                    x1="0"
                    y1="20"
                    x2="300"
                    y2="20"
                  />
                  <line
                    x1="0"
                    y1="70"
                    x2="300"
                    y2="70"
                  />
                  <line
                    x1="0"
                    y1="120"
                    x2="300"
                    y2="120"
                  />

                  <polyline
                    points={trendPolyline}
                    fill="none"
                  />

                  {trendPoints.map((point, index) => {
                    const x =
                      trendPoints.length === 1
                        ? 150
                        : (index * 300) /
                          (trendPoints.length - 1);

                    const y =
                      120 -
                      ((point.score - trendMin) /
                        trendRange) *
                        100;

                    return (
                      <g key={`${point.label}-${index}`}>
                        <circle
                          cx={x}
                          cy={y}
                          r="4"
                        />

                        <title>
                          {point.label}: {point.score}
                        </title>
                      </g>
                    );
                  })}
                </svg>
              </div>

              <div className="studio-seo-trend-labels">
                {trendPoints.map((point, index) => (
                  <span key={`${point.label}-${index}`}>
                    {point.label}
                  </span>
                ))}
              </div>
            </>
          ) : (
            <p className="studio-seo-history-empty">
              Save this article to create trend data.
            </p>
          )}
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

        <div className="studio-seo-snapshot-management">
          <div className="studio-seo-snapshot-selectors">
            <label>
              <span>Snapshot A</span>

              <select
                value={selectedSnapshotA}
                onChange={event =>
                  setSelectedSnapshotA(
                    event.target.value,
                  )
                }
              >
                <option value="">
                  Select older snapshot
                </option>

                {articleHistory.map(snapshot => (
                  <option
                    key={`a-${snapshot.savedAt}`}
                    value={snapshot.savedAt}
                  >
                    {new Date(
                      snapshot.savedAt,
                    ).toLocaleString()}
                    {" — "}
                    {snapshot.score}/100
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Snapshot B</span>

              <select
                value={selectedSnapshotB}
                onChange={event =>
                  setSelectedSnapshotB(
                    event.target.value,
                  )
                }
              >
                <option value="">
                  Select newer snapshot
                </option>

                {articleHistory.map(snapshot => (
                  <option
                    key={`b-${snapshot.savedAt}`}
                    value={snapshot.savedAt}
                  >
                    {new Date(
                      snapshot.savedAt,
                    ).toLocaleString()}
                    {" — "}
                    {snapshot.score}/100
                  </option>
                ))}
              </select>
            </label>
          </div>

          {snapshotA && snapshotB ? (
            <div className="studio-seo-selected-comparison">
              <div>
                <span>Selected score change</span>

                <strong
                  className={
                    selectedScoreDelta &&
                    selectedScoreDelta > 0
                      ? "seo-history-positive"
                      : selectedScoreDelta &&
                          selectedScoreDelta < 0
                        ? "seo-history-negative"
                        : "seo-history-neutral"
                  }
                >
                  {selectedScoreDelta &&
                  selectedScoreDelta > 0
                    ? `+${selectedScoreDelta}`
                    : `${selectedScoreDelta ?? 0}`}
                </strong>
              </div>

              <div>
                <span>Grade change</span>
                <strong>
                  {snapshotA.grade}
                  {" → "}
                  {snapshotB.grade}
                </strong>
              </div>

              <div className="studio-seo-selected-categories">
                {snapshotB.categories.map(category => {
                  const older =
                    snapshotA.categories.find(
                      item =>
                        item.id === category.id,
                    );

                  const delta =
                    category.score -
                    (older?.score ?? category.score);

                  return (
                    <article key={category.id}>
                      <strong>
                        {category.label}
                      </strong>

                      <span>
                        {older?.score ?? "N/A"}
                        {" → "}
                        {category.score}
                      </span>

                      <em
                        className={
                          delta > 0
                            ? "seo-history-positive"
                            : delta < 0
                              ? "seo-history-negative"
                              : "seo-history-neutral"
                        }
                      >
                        {delta > 0
                          ? `+${delta}`
                          : `${delta}`}
                      </em>
                    </article>
                  );
                })}
              </div>
            </div>
          ) : null}

          <div className="studio-seo-trend-export-actions">
            <button
              type="button"
              className="secondary-button"
              disabled={articleHistory.length === 0}
              onClick={exportSeoTrendJson}
            >
              Export trend JSON
            </button>

            <button
              type="button"
              className="secondary-button"
              disabled={articleHistory.length === 0}
              onClick={exportSeoTrendCsv}
            >
              Export trend CSV
            </button>

            <button
              type="button"
              className="secondary-button"
              disabled={seoHistory.length === 0}
              onClick={backupAllSeoHistory}
            >
              Backup all history
            </button>

            <label className="studio-seo-history-restore">
              <span>Restore backup</span>

              <input
                type="file"
                accept="application/json,.json"
                onChange={event => {
                  const file = event.target.files?.[0];

                  if (file) {
                    void restoreSeoHistoryBackup(file);
                  }

                  event.target.value = "";
                }}
              />
            </label>
          </div>

          <div className="studio-seo-history-actions">
            <button
              type="button"
              className="secondary-button"
              disabled={articleHistory.length === 0}
              onClick={clearCurrentArticleHistory}
            >
              Clear article history
            </button>

            <button
              type="button"
              className="text-button danger-link"
              disabled={seoHistory.length === 0}
              onClick={clearAllSeoHistory}
            >
              Clear all history
            </button>
          </div>
        </div>
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
    </>
  );
}