import type {
  CmsBlock,
  CmsDocument,
  CmsHeadingBlock,
} from "./document-types";

export type SeoCheck = {
  id: string;
  label: string;
  passed: boolean;
  detail: string;
  severity: "info" | "warning" | "error";
};

export type HeadingAnalysis = {
  counts: Record<1 | 2 | 3 | 4 | 5 | 6, number>;
  total: number;
  emptyCount: number;
  duplicateCount: number;
  skippedLevels: string[];
  hasValidHierarchy: boolean;
};

export type LinkKind =
  | "internal"
  | "external"
  | "anchor"
  | "email"
  | "telephone"
  | "invalid";

export type LinkIssue =
  | "empty-url"
  | "placeholder-anchor"
  | "unsafe-javascript"
  | "missing-anchor-text"
  | "weak-anchor-text"
  | "duplicate-url"
  | "missing-external-security";

export type LinkRecord = {
  id: string;
  url: string;
  anchorText: string;
  kind: LinkKind;
  source: string;
  targetBlank: boolean;
  rel: string[];
  nofollow: boolean;
  sponsored: boolean;
  ugc: boolean;
  issues: LinkIssue[];
};

export type LinkAnalysis = {
  total: number;
  internal: number;
  external: number;
  anchor: number;
  invalid: number;
  duplicates: number;
  issueCount: number;
  records: LinkRecord[];
};

export type SeoScoreBreakdownItem = {
  id: string;
  label: string;
  points: number;
  earned: number;
  passed: boolean;
  detail: string;
};

export type KeywordAnalysis = {
  keyword: string;
  occurrences: number;
  density: number;
  inTitle: boolean;
  inMetaTitle: boolean;
  inMetaDescription: boolean;
  inSlug: boolean;
  inH1: boolean;
  inFirstParagraph: boolean;
  inLastParagraph: boolean;
  h2Count: number;
  h3Count: number;
};

export type ReadabilityAnalysis = {
  score: number;
  label: "Easy" | "Good" | "Improve" | "Difficult";
  sentenceCount: number;
  paragraphCount: number;
  averageSentenceWords: number;
  longSentenceCount: number;
  longParagraphCount: number;
};

export type SeoDocumentAnalysis = {
  seoScore: number;
  contentScore: number;
  wordCount: number;
  readingTimeMinutes: number;
  headings: HeadingAnalysis;
  links: LinkAnalysis;
  checks: SeoCheck[];
  scoreBreakdown: SeoScoreBreakdownItem[];
  keywordAnalysis: KeywordAnalysis;
  readability: ReadabilityAnalysis;
};

function looksLikeHtml(value: string): boolean {
  return /<\/?(?:html|body|main|article|section|aside|nav|header|footer|div|span|h[1-6]|p|ul|ol|li|table|thead|tbody|tr|th|td|blockquote|figure|figcaption|img|a|hr|br|details|summary)\b[^>]*>/i.test(
    String(value || ""),
  );
}

function stripHtml(value: string): string {
  return String(value || "")
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ")
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/\s+/g, " ")
    .trim();
}

function blockText(block: CmsBlock): string {
  switch (block.type) {
    case "paragraph":
    case "quote":
      return stripHtml(block.html);

    case "heading":
      return block.text.trim();

    case "table":
      return stripHtml(block.html);

    case "code":
      return (
        block.language === "html" ||
        looksLikeHtml(block.code)
      )
        ? stripHtml(block.code)
        : block.code;

    case "button":
      return `${block.label} ${block.url}`;

    case "youtube":
      return `${block.title} ${block.url}`;

    case "accordion":
      return block.items
        .map(item => `${item.title} ${stripHtml(item.html)}`)
        .join(" ");

    case "image":
      return `${block.alt} ${block.caption} ${block.linkUrl}`;

    case "gallery":
    case "divider":
      return "";
  }
}

function documentText(document: CmsDocument): string {
  return [
    document.title,
    document.excerpt,
    ...document.blocks.map(blockText),
  ]
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
}

function countWords(value: string): number {
  if (!value.trim()) return 0;

  return value
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .length;
}

function analyzeHeadings(
  blocks: CmsBlock[],
): HeadingAnalysis {
  const counts: HeadingAnalysis["counts"] = {
    1: 0,
    2: 0,
    3: 0,
    4: 0,
    5: 0,
    6: 0,
  };

  const entries: Array<{
    level: 1 | 2 | 3 | 4 | 5 | 6;
    text: string;
  }> = [];

  for (const block of blocks) {
    if (block.type === "heading") {
      entries.push({
        level: block.level,
        text: block.text,
      });
      continue;
    }

    if (
      block.type === "code" &&
      (
        block.language === "html" ||
        looksLikeHtml(block.code)
      )
    ) {
      const pattern =
        /<h([1-6])\b[^>]*>([\s\S]*?)<\/h\1>/gi;

      let match: RegExpExecArray | null;

      while ((match = pattern.exec(block.code)) !== null) {
        entries.push({
          level: Number(match[1]) as
            | 1 | 2 | 3 | 4 | 5 | 6,
          text: stripHtml(match[2]),
        });
      }
    }
  }

  const normalizedTexts = new Map<string, number>();
  const skippedLevels: string[] = [];
  let emptyCount = 0;
  let previousLevel: number | null = null;

  for (const heading of entries) {
    counts[heading.level] += 1;

    const headingText = heading.text.trim();

    if (!headingText) {
      emptyCount += 1;
    } else {
      const normalized = headingText
        .toLowerCase()
        .replace(/\s+/g, " ");

      normalizedTexts.set(
        normalized,
        (normalizedTexts.get(normalized) || 0) + 1,
      );
    }

    if (
      previousLevel !== null &&
      heading.level > previousLevel + 1
    ) {
      skippedLevels.push(
        `H${previousLevel} → H${heading.level}`,
      );
    }

    previousLevel = heading.level;
  }

  const duplicateCount = Array.from(
    normalizedTexts.values(),
  ).reduce(
    (total, count) =>
      total + (count > 1 ? count - 1 : 0),
    0,
  );

  return {
    counts,
    total: entries.length,
    emptyCount,
    duplicateCount,
    skippedLevels,
    hasValidHierarchy:
      counts[1] === 1 &&
      emptyCount === 0 &&
      skippedLevels.length === 0,
  };
}

function classifyLink(url: string): LinkKind {
  const normalized = url.trim();

  if (!normalized) return "invalid";
  if (/^javascript:/i.test(normalized)) return "invalid";
  if (/^mailto:/i.test(normalized)) return "email";
  if (/^tel:/i.test(normalized)) return "telephone";
  if (normalized.startsWith("#")) return "anchor";

  if (
    normalized.startsWith("/") ||
    /^(?:https?:\/\/)?(?:www\.)?venusrealm\.net(?:\/|$)/i.test(
      normalized,
    )
  ) {
    return "internal";
  }

  if (/^https?:\/\//i.test(normalized)) {
    return "external";
  }

  return "invalid";
}

function normalizeAnchorText(value: string): string {
  return stripHtml(value)
    .replace(/\s+/g, " ")
    .trim();
}

function weakAnchorText(value: string): boolean {
  const normalized = value
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();

  return new Set([
    "click here",
    "read more",
    "learn more",
    "here",
    "link",
    "website",
    "this page",
    "more",
  ]).has(normalized);
}

function extractAttribute(
  attributes: string,
  name: string,
): string {
  const pattern = new RegExp(
    `\\\\b${name}\\\\s*=\\\\s*(?:"([^"]*)"|'([^']*)'|([^\\\\s>]+))`,
    "i",
  );

  const match = attributes.match(pattern);

  return String(
    match?.[1] ??
    match?.[2] ??
    match?.[3] ??
    "",
  ).trim();
}

function extractHtmlLinks(
  html: string,
  source: string,
): Array<Omit<LinkRecord, "id" | "issues">> {
  const records: Array<Omit<LinkRecord, "id" | "issues">> = [];
  const pattern =
    /<a\b([^>]*)>([\s\S]*?)<\/a>/gi;

  let match: RegExpExecArray | null;

  while ((match = pattern.exec(html)) !== null) {
    const attributes = match[1] || "";
    const url = extractAttribute(attributes, "href");
    const target = extractAttribute(attributes, "target");
    const relValue = extractAttribute(attributes, "rel");

    const rel = relValue
      .toLowerCase()
      .split(/\s+/)
      .filter(Boolean);

    records.push({
      url,
      anchorText: normalizeAnchorText(match[2]),
      kind: classifyLink(url),
      source,
      targetBlank: target.toLowerCase() === "_blank",
      rel,
      nofollow: rel.includes("nofollow"),
      sponsored: rel.includes("sponsored"),
      ugc: rel.includes("ugc"),
    });
  }

  return records;
}

function detectLinks(document: CmsDocument): LinkAnalysis {
  const rawRecords: Array<Omit<LinkRecord, "id" | "issues">> = [];

  for (const block of document.blocks) {
    switch (block.type) {
      case "button":
        rawRecords.push({
          url: block.url,
          anchorText: block.label,
          kind: classifyLink(block.url),
          source: "Button block",
          targetBlank: false,
          rel: [],
          nofollow: false,
          sponsored: false,
          ugc: false,
        });
        break;

      case "youtube":
        rawRecords.push({
          url: block.url,
          anchorText: block.title || "YouTube video",
          kind: classifyLink(block.url),
          source: "YouTube block",
          targetBlank: false,
          rel: [],
          nofollow: false,
          sponsored: false,
          ugc: false,
        });
        break;

      case "image":
        if (block.linkUrl) {
          rawRecords.push({
            url: block.linkUrl,
            anchorText:
              block.alt ||
              block.caption ||
              "Linked image",
            kind: classifyLink(block.linkUrl),
            source: "Image block",
            targetBlank: false,
            rel: [],
            nofollow: false,
            sponsored: false,
            ugc: false,
          });
        }
        break;

      case "paragraph":
      case "quote":
      case "table":
        rawRecords.push(
          ...extractHtmlLinks(
            block.html,
            `${block.type} block`,
          ),
        );
        break;

      case "code":
        if (
          block.language === "html" ||
          looksLikeHtml(block.code)
        ) {
          rawRecords.push(
            ...extractHtmlLinks(
              block.code,
              "Imported HTML",
            ),
          );
        }
        break;

      case "accordion":
        for (const item of block.items) {
          rawRecords.push(
            ...extractHtmlLinks(
              item.html,
              `Accordion: ${item.title || "Untitled item"}`,
            ),
          );
        }
        break;

      case "heading":
      case "gallery":
      case "divider":
        break;
    }
  }

  const normalizedCounts = new Map<string, number>();

  for (const record of rawRecords) {
    const normalizedUrl = record.url.trim().toLowerCase();

    if (!normalizedUrl) continue;

    normalizedCounts.set(
      normalizedUrl,
      (normalizedCounts.get(normalizedUrl) || 0) + 1,
    );
  }

  const records: LinkRecord[] = rawRecords.map(
    (record, index) => {
      const issues: LinkIssue[] = [];
      const normalizedUrl =
        record.url.trim().toLowerCase();

      if (!record.url.trim()) {
        issues.push("empty-url");
      }

      if (record.url.trim() === "#") {
        issues.push("placeholder-anchor");
      }

      if (/^javascript:/i.test(record.url.trim())) {
        issues.push("unsafe-javascript");
      }

      if (!record.anchorText.trim()) {
        issues.push("missing-anchor-text");
      } else if (weakAnchorText(record.anchorText)) {
        issues.push("weak-anchor-text");
      }

      if (
        normalizedUrl &&
        (normalizedCounts.get(normalizedUrl) || 0) > 1
      ) {
        issues.push("duplicate-url");
      }

      if (
        record.kind === "external" &&
        (
          !record.targetBlank ||
          !record.rel.includes("noopener") ||
          !record.rel.includes("noreferrer")
        )
      ) {
        issues.push("missing-external-security");
      }

      return {
        ...record,
        id: `link-${index + 1}`,
        issues,
      };
    },
  );

  return {
    total: records.length,
    internal: records.filter(
      record => record.kind === "internal",
    ).length,
    external: records.filter(
      record => record.kind === "external",
    ).length,
    anchor: records.filter(
      record => record.kind === "anchor",
    ).length,
    invalid: records.filter(
      record => record.kind === "invalid",
    ).length,
    duplicates: records.filter(
      record =>
        record.issues.includes("duplicate-url"),
    ).length,
    issueCount: records.reduce(
      (total, record) => total + record.issues.length,
      0,
    ),
    records,
  };
}

export function analyzeSeoDocument(
  document: CmsDocument,
): SeoDocumentAnalysis {
  const text = documentText(document);
  const wordCount = countWords(text);

  const readingTimeMinutes = Math.max(
    1,
    Math.ceil(wordCount / 220),
  );

  const sentenceTexts = text
    .split(/[.!?]+/)
    .map(sentence => sentence.trim())
    .filter(Boolean);

  const sentenceCount = sentenceTexts.length;

  const averageSentenceWords =
    sentenceCount > 0
      ? Number(
          (
            sentenceTexts.reduce(
              (total, sentence) =>
                total + countWords(sentence),
              0,
            ) / sentenceCount
          ).toFixed(1),
        )
      : 0;

  const longSentenceCount = sentenceTexts.filter(
    sentence => countWords(sentence) > 25,
  ).length;

  const paragraphTexts = document.blocks
    .filter(
      block =>
        block.type === "paragraph" ||
        block.type === "quote",
    )
    .map(block =>
      block.type === "paragraph" ||
      block.type === "quote"
        ? stripHtml(block.html)
        : "",
    )
    .filter(Boolean);

  const paragraphCount = paragraphTexts.length;

  const longParagraphCount = paragraphTexts.filter(
    paragraph => countWords(paragraph) > 120,
  ).length;

  const readabilityScore = Math.max(
    0,
    Math.min(
      100,
      100 -
        Math.max(0, averageSentenceWords - 18) * 3 -
        longSentenceCount * 4 -
        longParagraphCount * 8,
    ),
  );

  const roundedReadabilityScore = Math.round(
    readabilityScore,
  );

  const readabilityLabel: ReadabilityAnalysis["label"] =
    roundedReadabilityScore >= 85
      ? "Easy"
      : roundedReadabilityScore >= 70
        ? "Good"
        : roundedReadabilityScore >= 50
          ? "Improve"
          : "Difficult";

  const headings = analyzeHeadings(document.blocks);
  const links = detectLinks(document);

  const images = document.blocks.filter(
    block => block.type === "image",
  );

  const missingAltImages = images.filter(
    block =>
      block.type === "image" &&
      !block.alt.trim(),
  );

  const hasFaq = document.blocks.some(
    block =>
      block.type === "accordion" ||
      (
        block.type === "code" &&
        (
          block.language === "html" ||
          looksLikeHtml(block.code)
        ) &&
        /<(?:details|summary)\b/i.test(block.code)
      ),
  );

  const hasTable = document.blocks.some(
    block =>
      block.type === "table" ||
      (
        block.type === "code" &&
        (
          block.language === "html" ||
          looksLikeHtml(block.code)
        ) &&
        /<table\b/i.test(block.code)
      ),
  );

  const hasRiskDisclaimer =
    /risk|not guaranteed|educational|financial advice/i.test(
      text,
    );

  const title = document.title.trim();
  const slug = document.slug.trim();
  const keyword =
    document.seo.focusKeyword.trim().toLowerCase();

  const normalizedKeyword = keyword;

  const occurrences =
    normalizedKeyword
      ? (
          text.toLowerCase().match(
            new RegExp(
              normalizedKeyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"),
              "g",
            ),
          ) || []
        ).length
      : 0;

  const density =
    wordCount > 0
      ? Number(
          ((occurrences / wordCount) * 100).toFixed(2),
        )
      : 0;

  const metaTitle = document.seo.metaTitle.trim();
  const metaDescription =
    document.seo.metaDescription.trim();
  const canonical =
    document.seo.canonicalUrl.trim();

  const checks: SeoCheck[] = [
    {
      id: "single-h1",
      label: "Single H1",
      passed: headings.counts[1] === 1,
      detail:
        headings.counts[1] === 0
          ? "H1 missing"
          : headings.counts[1] === 1
            ? "Exactly one H1"
            : `${headings.counts[1]} H1 headings found`,
      severity:
        headings.counts[1] === 1
          ? "info"
          : "error",
    },
    {
      id: "heading-hierarchy",
      label: "H1–H6 hierarchy",
      passed:
        headings.skippedLevels.length === 0,
      detail:
        headings.skippedLevels.length === 0
          ? "No skipped heading levels"
          : `Skipped: ${headings.skippedLevels.join(", ")}`,
      severity:
        headings.skippedLevels.length === 0
          ? "info"
          : "error",
    },
    {
      id: "empty-headings",
      label: "Empty headings",
      passed: headings.emptyCount === 0,
      detail:
        headings.emptyCount === 0
          ? "No empty headings"
          : `${headings.emptyCount} empty headings`,
      severity:
        headings.emptyCount === 0
          ? "info"
          : "error",
    },
    {
      id: "duplicate-headings",
      label: "Duplicate headings",
      passed: headings.duplicateCount === 0,
      detail:
        headings.duplicateCount === 0
          ? "No duplicate headings"
          : `${headings.duplicateCount} duplicate headings`,
      severity:
        headings.duplicateCount === 0
          ? "info"
          : "warning",
    },
    {
      id: "article-length",
      label: "Article length",
      passed: wordCount >= 600,
      detail: `${wordCount} words; 600+ recommended`,
      severity:
        wordCount >= 600 ? "info" : "warning",
    },
    {
      id: "excerpt",
      label: "Article excerpt",
      passed: document.excerpt.trim().length >= 80,
      detail: `${document.excerpt.trim().length} characters`,
      severity:
        document.excerpt.trim().length >= 80
          ? "info"
          : "warning",
    },
    {
      id: "image-alt",
      label: "Image alt text",
      passed:
        images.length > 0 &&
        missingAltImages.length === 0,
      detail:
        images.length === 0
          ? "No image blocks"
          : `${missingAltImages.length} missing alt text`,
      severity:
        images.length > 0 &&
        missingAltImages.length === 0
          ? "info"
          : "warning",
    },
    {
      id: "internal-links",
      label: "Internal links",
      passed: links.internal >= 1,
      detail: `${links.internal} internal links`,
      severity:
        links.internal >= 1 ? "info" : "warning",
    },
    {
      id: "external-links",
      label: "External links",
      passed: links.external >= 1,
      detail: `${links.external} external links`,
      severity:
        links.external >= 1 ? "info" : "warning",
    },
    {
      id: "link-validity",
      label: "Link validity",
      passed: links.invalid === 0,
      detail:
        links.invalid === 0
          ? "No invalid or unsafe links"
          : `${links.invalid} invalid or unsafe links`,
      severity:
        links.invalid === 0 ? "info" : "error",
    },
    {
      id: "link-quality",
      label: "Link quality",
      passed: links.issueCount === 0,
      detail:
        links.issueCount === 0
          ? "No link quality issues"
          : `${links.issueCount} link issues detected`,
      severity:
        links.issueCount === 0 ? "info" : "warning",
    },
    {
      id: "faq",
      label: "FAQ block",
      passed: hasFaq,
      detail: hasFaq
        ? "FAQ/Accordion available"
        : "Add FAQ when useful",
      severity: hasFaq ? "info" : "warning",
    },
    {
      id: "table",
      label: "Comparison table",
      passed: hasTable,
      detail: hasTable
        ? "Table available"
        : "Add table when useful",
      severity: hasTable ? "info" : "warning",
    },
    {
      id: "risk-disclaimer",
      label: "Risk disclaimer",
      passed: hasRiskDisclaimer,
      detail: hasRiskDisclaimer
        ? "Risk wording detected"
        : "Add educational risk disclaimer",
      severity:
        hasRiskDisclaimer ? "info" : "warning",
    },
  ];

  let seoScore = 0;
  const scoreBreakdown: SeoScoreBreakdownItem[] = [];

  if (title.length >= 30 && title.length <= 70) {
    scoreBreakdown.push({
      id: "title",
      label: "Title Length",
      points: 10,
      earned: 10,
      passed: true,
      detail: "Title length is optimal.",
    });
    seoScore += 10;
  } else {
    scoreBreakdown.push({
      id: "title",
      label: "Title Length",
      points: 10,
      earned: 0,
      passed: false,
      detail: "Recommended: 30–70 characters.",
    });
  }

  if (
    metaTitle.length >= 30 &&
    metaTitle.length <= 60
  ) {
    scoreBreakdown.push({
      id: "meta-title",
      label: "Meta Title",
      points: 15,
      earned: 15,
      passed: true,
      detail: "Meta title is optimized.",
    });
    seoScore += 15;
  } else {
    scoreBreakdown.push({
      id: "meta-title",
      label: "Meta Title",
      points: 15,
      earned: 0,
      passed: false,
      detail: "Recommended: 30–60 characters.",
    });
  }

  if (
    metaDescription.length >= 120 &&
    metaDescription.length <= 160
  ) {
    scoreBreakdown.push({
      id: "meta-description",
      label: "Meta Description",
      points: 15,
      earned: 15,
      passed: true,
      detail: "Meta description is optimized.",
    });
    seoScore += 15;
  } else {
    scoreBreakdown.push({
      id: "meta-description",
      label: "Meta Description",
      points: 15,
      earned: 0,
      passed: false,
      detail: "Recommended: 120–160 characters.",
    });
  }

  if (slug.length >= 5 && slug.length <= 80) {
    seoScore += 10;
  }

  if (
    keyword &&
    title.toLowerCase().includes(keyword)
  ) {
    seoScore += 10;
  }

  if (
    keyword &&
    document.excerpt
      .toLowerCase()
      .includes(keyword)
  ) {
    seoScore += 5;
  }

  if (canonical) {
    scoreBreakdown.push({
      id: "canonical",
      label: "Canonical URL",
      points: 5,
      earned: 5,
      passed: true,
      detail: "Canonical URL configured.",
    });
    seoScore += 5;
  } else {
    scoreBreakdown.push({
      id: "canonical",
      label: "Canonical URL",
      points: 5,
      earned: 0,
      passed: false,
      detail: "Canonical URL missing.",
    });
  }

  if (headings.counts[1] === 1) {
    seoScore += 10;
  }

  if (headings.skippedLevels.length === 0) {
    seoScore += 5;
  }

  if (headings.emptyCount === 0) {
    seoScore += 5;
  }

  if (wordCount >= 600) {
    seoScore += 5;
  }

  if (
    images.length > 0 &&
    missingAltImages.length === 0
  ) {
    scoreBreakdown.push({
      id: "images",
      label: "Image ALT",
      points: 5,
      earned: 5,
      passed: true,
      detail: "All images contain ALT text.",
    });
    seoScore += 5;
  } else {
    scoreBreakdown.push({
      id: "images",
      label: "Image ALT",
      points: 5,
      earned: 0,
      passed: false,
      detail: "Some images are missing ALT text.",
    });
  }

  const passedChecks = checks.filter(
    check => check.passed,
  ).length;

  const contentScore = Math.round(
    (passedChecks / checks.length) * 100,
  );

  return {
    seoScore: Math.min(seoScore, 100),
    contentScore,
    wordCount,
    readingTimeMinutes,
    headings,
    links,
    checks,
    scoreBreakdown,
    keywordAnalysis: {
      keyword,
      occurrences,
      density,
      inTitle:
        normalizedKeyword.length > 0 &&
        title.toLowerCase().includes(normalizedKeyword),
      inMetaTitle:
        normalizedKeyword.length > 0 &&
        metaTitle.toLowerCase().includes(normalizedKeyword),
      inMetaDescription:
        normalizedKeyword.length > 0 &&
        metaDescription
          .toLowerCase()
          .includes(normalizedKeyword),
      inSlug:
        normalizedKeyword.length > 0 &&
        slug.toLowerCase().includes(normalizedKeyword),
      inH1: headings.counts[1] > 0,
      inFirstParagraph: false,
      inLastParagraph: false,
      h2Count: headings.counts[2],
      h3Count: headings.counts[3],
    },
    readability: {
      score: roundedReadabilityScore,
      label: readabilityLabel,
      sentenceCount,
      paragraphCount,
      averageSentenceWords,
      longSentenceCount,
      longParagraphCount,
    },
  };
}
