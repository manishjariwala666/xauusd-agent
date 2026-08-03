"use client";

import type {
  CmsBlock,
  CmsDocument,
} from "@/lib/editor-v2/document-types";

type CheckResult = {
  label: string;
  passed: boolean;
  detail: string;
};

function stripHtml(value: string): string {
  return value
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function blockText(block: CmsBlock): string {
  switch (block.type) {
    case "paragraph":
    case "quote":
      return stripHtml(block.html);

    case "heading":
      return block.text;

    case "table":
      return stripHtml(block.html);

    case "code":
      return block.code;

    case "button":
      return `${block.label} ${block.url}`;

    case "youtube":
      return `${block.title} ${block.url}`;

    case "accordion":
      return block.items
        .map(item => `${item.title} ${stripHtml(item.html)}`)
        .join(" ");

    case "image":
      return `${block.alt} ${block.caption}`;

    case "gallery":
    case "divider":
      return "";
  }
}

function articleText(document: CmsDocument): string {
  return [
    document.title,
    document.excerpt,
    ...document.blocks.map(blockText),
  ]
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
}

function wordCount(value: string): number {
  return value
    .split(/\s+/)
    .filter(Boolean)
    .length;
}

function calculateSeoScore(document: CmsDocument): number {
  let score = 0;

  const keyword =
    document.seo.focusKeyword.trim().toLowerCase();

  const title = document.title.trim();
  const metaTitle = document.seo.metaTitle.trim();
  const metaDescription =
    document.seo.metaDescription.trim();

  if (title.length >= 30 && title.length <= 70) {
    score += 15;
  }

  if (
    metaTitle.length >= 30 &&
    metaTitle.length <= 60
  ) {
    score += 20;
  }

  if (
    metaDescription.length >= 120 &&
    metaDescription.length <= 160
  ) {
    score += 20;
  }

  if (
    document.slug.length >= 5 &&
    document.slug.length <= 80
  ) {
    score += 15;
  }

  if (
    keyword &&
    title.toLowerCase().includes(keyword)
  ) {
    score += 15;
  }

  if (
    keyword &&
    document.excerpt
      .toLowerCase()
      .includes(keyword)
  ) {
    score += 10;
  }

  if (document.seo.canonicalUrl.trim()) {
    score += 5;
  }

  return Math.min(score, 100);
}

function buildContentChecks(
  document: CmsDocument,
): CheckResult[] {
  const text = articleText(document);
  const words = wordCount(text);

  const headings = document.blocks.filter(
    block => block.type === "heading",
  );

  const images = document.blocks.filter(
    block => block.type === "image",
  );

  const missingAltImages = images.filter(
    block =>
      block.type === "image" &&
      !block.alt.trim(),
  );

  const links =
    document.blocks.filter(
      block =>
        block.type === "button" ||
        block.type === "youtube",
    ).length +
    (text.match(/https?:\/\//g) || []).length;

  const hasFaq = document.blocks.some(
    block => block.type === "accordion",
  );

  const hasTable = document.blocks.some(
    block => block.type === "table",
  );

  const hasRiskDisclaimer =
    /risk|not guaranteed|educational|financial advice/i
      .test(text);

  return [
    {
      label: "Article length",
      passed: words >= 600,
      detail: `${words} words; 600+ recommended`,
    },
    {
      label: "Heading structure",
      passed: headings.length >= 3,
      detail: `${headings.length} heading blocks`,
    },
    {
      label: "Article excerpt",
      passed:
        document.excerpt.trim().length >= 80,
      detail: `${document.excerpt.trim().length} characters`,
    },
    {
      label: "Image alt text",
      passed:
        images.length === 0 ||
        missingAltImages.length === 0,
      detail:
        images.length === 0
          ? "No image blocks"
          : `${missingAltImages.length} missing alt text`,
    },
    {
      label: "Useful links",
      passed: links >= 1,
      detail: `${links} detectable links`,
    },
    {
      label: "FAQ block",
      passed: hasFaq,
      detail: hasFaq
        ? "FAQ/Accordion available"
        : "Add FAQ/Accordion block",
    },
    {
      label: "Comparison table",
      passed: hasTable,
      detail: hasTable
        ? "Table available"
        : "Add table when useful",
    },
    {
      label: "Risk disclaimer",
      passed: hasRiskDisclaimer,
      detail: hasRiskDisclaimer
        ? "Risk wording detected"
        : "Add clear educational risk disclaimer",
    },
  ];
}

export function ContentInsightsPanel({
  document,
}: {
  document: CmsDocument;
}) {
  const seoScore = calculateSeoScore(document);
  const checks = buildContentChecks(document);

  const passedChecks = checks.filter(
    check => check.passed,
  ).length;

  const contentScore = Math.round(
    (passedChecks / checks.length) * 100,
  );

  return (
    <aside className="studio-insights-panel">
      <section className="studio-insight-card">
        <header>
          <div>
            <span>SEO SCORE</span>
            <h2>{seoScore}/100</h2>
          </div>

          <div
            className={`studio-score-badge ${
              seoScore >= 80
                ? "good"
                : seoScore >= 50
                  ? "warning"
                  : "poor"
            }`}
          >
            {seoScore >= 80
              ? "Good"
              : seoScore >= 50
                ? "Improve"
                : "Needs work"}
          </div>
        </header>

        <div className="studio-score-progress">
          <span style={{ width: `${seoScore}%` }} />
        </div>

        <ul>
          <li>
            {document.seo.focusKeyword
              ? "✓"
              : "○"}{" "}
            Focus keyword
          </li>
          <li>
            {document.seo.metaTitle
              ? "✓"
              : "○"}{" "}
            Meta title
          </li>
          <li>
            {document.seo.metaDescription
              ? "✓"
              : "○"}{" "}
            Meta description
          </li>
          <li>
            {document.seo.canonicalUrl
              ? "✓"
              : "○"}{" "}
            Canonical URL
          </li>
        </ul>

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
            <h2>{contentScore}/100</h2>
          </div>

          <strong>
            {passedChecks}/{checks.length}
          </strong>
        </header>

        <div className="studio-content-check-list">
          {checks.map(check => (
            <article
              key={check.label}
              className={
                check.passed
                  ? "check-passed"
                  : "check-warning"
              }
            >
              <span>
                {check.passed ? "✓" : "!"}
              </span>

              <div>
                <strong>{check.label}</strong>
                <small>{check.detail}</small>
              </div>
            </article>
          ))}
        </div>
      </section>

      <p className="studio-insights-note">
        Scores deterministic guidance hain. Search
        ranking ya trading results guarantee nahi hain.
      </p>
    </aside>
  );
}
