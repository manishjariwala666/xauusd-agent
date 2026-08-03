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

export type SeoDocumentAnalysis = {
  seoScore: number;
  contentScore: number;
  wordCount: number;
  readingTimeMinutes: number;
  headings: HeadingAnalysis;
  checks: SeoCheck[];
};

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
  const headings = blocks.filter(
    (block): block is CmsHeadingBlock =>
      block.type === "heading",
  );

  const counts: HeadingAnalysis["counts"] = {
    1: 0,
    2: 0,
    3: 0,
    4: 0,
    5: 0,
    6: 0,
  };

  const normalizedTexts = new Map<string, number>();
  const skippedLevels: string[] = [];
  let emptyCount = 0;
  let previousLevel: number | null = null;

  for (const heading of headings) {
    counts[heading.level] += 1;

    const text = heading.text.trim();

    if (!text) {
      emptyCount += 1;
    } else {
      const normalized = text.toLowerCase().replace(/\s+/g, " ");
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

  const hasValidHierarchy =
    counts[1] === 1 &&
    emptyCount === 0 &&
    skippedLevels.length === 0;

  return {
    counts,
    total: headings.length,
    emptyCount,
    duplicateCount,
    skippedLevels,
    hasValidHierarchy,
  };
}

function detectLinks(document: CmsDocument): {
  total: number;
  internal: number;
  external: number;
} {
  const urls: string[] = [];

  for (const block of document.blocks) {
    if (block.type === "button" && block.url) {
      urls.push(block.url);
    }

    if (block.type === "youtube" && block.url) {
      urls.push(block.url);
    }

    if (
      block.type === "image" &&
      block.linkUrl
    ) {
      urls.push(block.linkUrl);
    }

    if (
      block.type === "paragraph" ||
      block.type === "quote" ||
      block.type === "table"
    ) {
      const matches = block.html.match(
        /href=["']([^"']+)["']/gi,
      );

      for (const match of matches || []) {
        const url = match.match(
          /href=["']([^"']+)["']/i,
        )?.[1];

        if (url) urls.push(url);
      }
    }
  }

  let internal = 0;
  let external = 0;

  for (const url of urls) {
    if (
      url.startsWith("/") ||
      /(?:^https?:\/\/)?(?:www\.)?venusrealm\.net/i.test(url)
    ) {
      internal += 1;
    } else if (/^https?:\/\//i.test(url)) {
      external += 1;
    }
  }

  return {
    total: urls.length,
    internal,
    external,
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
    block => block.type === "accordion",
  );

  const hasTable = document.blocks.some(
    block => block.type === "table",
  );

  const hasRiskDisclaimer =
    /risk|not guaranteed|educational|financial advice/i.test(
      text,
    );

  const title = document.title.trim();
  const slug = document.slug.trim();
  const keyword =
    document.seo.focusKeyword.trim().toLowerCase();
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

  if (title.length >= 30 && title.length <= 70) {
    seoScore += 10;
  }

  if (
    metaTitle.length >= 30 &&
    metaTitle.length <= 60
  ) {
    seoScore += 15;
  }

  if (
    metaDescription.length >= 120 &&
    metaDescription.length <= 160
  ) {
    seoScore += 15;
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
    seoScore += 5;
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
    seoScore += 5;
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
    checks,
  };
}
