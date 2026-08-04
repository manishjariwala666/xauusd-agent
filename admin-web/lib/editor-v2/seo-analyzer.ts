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

export type PublishChecklistItem = {
  id: string;
  label: string;
  passed: boolean;
  required: boolean;
  detail: string;
};

export type PublishChecklist = {
  ready: boolean;
  passed: number;
  total: number;
  items: PublishChecklistItem[];
};

export type ImageSeoRecord = {
  id: string;
  src: string;
  alt: string;
  caption: string;
  width: number | null;
  height: number | null;
  external: boolean;
  issues: string[];
};

export type ImageSeoAnalysis = {
  score: number;
  total: number;
  missingAlt: number;
  missingSource: number;
  missingDimensions: number;
  missingCaption: number;
  externalSources: number;
  largeDimensions: number;
  issueCount: number;
  records: ImageSeoRecord[];
};

export type SchemaHealthCheck = {
  id: string;
  label: string;
  passed: boolean;
  required: boolean;
  detail: string;
};

export type SchemaHealthAnalysis = {
  score: number;
  present: boolean;
  validObject: boolean;
  schemaType: string;
  passed: number;
  total: number;
  checks: SchemaHealthCheck[];
};

export type SocialPreviewCheck = {
  id: string;
  label: string;
  passed: boolean;
  detail: string;
};

export type SocialPreviewAnalysis = {
  score: number;
  title: string;
  description: string;
  url: string;
  image: string;
  sharingEnabled: boolean;
  platforms: string[];
  passed: number;
  total: number;
  checks: SocialPreviewCheck[];
};

export type SeoHealthCategory = {
  id:
    | "seo"
    | "content"
    | "readability"
    | "images"
    | "schema"
    | "social"
    | "publish";
  label: string;
  score: number;
  weight: number;
  status: "good" | "warning" | "critical";
};

export type SeoHealthPriorityIssue = {
  id: string;
  label: string;
  detail: string;
  source: string;
  severity: "critical" | "warning";
};

export type AdvancedSeoHealthAnalysis = {
  score: number;
  grade: "A+" | "A" | "B" | "C" | "D" | "F";
  label: "Excellent" | "Good" | "Improve" | "Critical";
  ready: boolean;
  criticalCount: number;
  warningCount: number;
  categories: SeoHealthCategory[];
  priorityIssues: SeoHealthPriorityIssue[];
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
  publishChecklist: PublishChecklist;
  imageSeo: ImageSeoAnalysis;
  schemaHealth: SchemaHealthAnalysis;
  socialPreview: SocialPreviewAnalysis;
  advancedHealth: AdvancedSeoHealthAnalysis;
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

  const imageSeoRecords: ImageSeoRecord[] = images.map(
    block => {
      const src = block.src.trim();
      const alt = block.alt.trim();
      const caption = block.caption.trim();

      const external =
        /^https?:\/\//i.test(src) &&
        !/^https:\/\/(?:www\.)?venusrealm\.net(?:\/|$)/i.test(
          src,
        );

      const issues: string[] = [];

      if (!src) issues.push("Missing image source");
      if (!alt) issues.push("Missing ALT text");
      if (!caption) issues.push("Missing caption");

      if (!block.width || !block.height) {
        issues.push("Missing width or height");
      }

      if (
        (block.width && block.width > 2400) ||
        (block.height && block.height > 2400)
      ) {
        issues.push("Large image dimensions");
      }

      if (external) {
        issues.push("External image source");
      }

      return {
        id: block.id,
        src,
        alt,
        caption,
        width: block.width,
        height: block.height,
        external,
        issues,
      };
    },
  );

  const missingSourceImages = imageSeoRecords.filter(
    image => !image.src,
  ).length;

  const missingDimensionImages = imageSeoRecords.filter(
    image => !image.width || !image.height,
  ).length;

  const missingCaptionImages = imageSeoRecords.filter(
    image => !image.caption,
  ).length;

  const externalImageSources = imageSeoRecords.filter(
    image => image.external,
  ).length;

  const largeDimensionImages = imageSeoRecords.filter(
    image =>
      (image.width && image.width > 2400) ||
      (image.height && image.height > 2400),
  ).length;

  const imageIssueCount = imageSeoRecords.reduce(
    (total, image) => total + image.issues.length,
    0,
  );

  const imageSeoScore =
    images.length === 0
      ? 100
      : Math.max(
          0,
          Math.round(
            100 -
              missingAltImages.length * 25 -
              missingSourceImages * 30 -
              missingDimensionImages * 10 -
              missingCaptionImages * 5 -
              externalImageSources * 5 -
              largeDimensionImages * 10,
          ),
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

  const schemaValue = document.seo.schemaJsonLd;

  const schemaPresent =
    schemaValue !== null &&
    typeof schemaValue === "object";

  const schemaObject =
    schemaPresent &&
    !Array.isArray(schemaValue)
      ? schemaValue as Record<string, unknown>
      : null;

  const schemaString = (key: string): string =>
    typeof schemaObject?.[key] === "string"
      ? String(schemaObject[key]).trim()
      : "";

  const schemaContext = schemaString("@context");
  const schemaType = schemaString("@type");
  const schemaHeadline = schemaString("headline");
  const schemaDescription = schemaString("description");
  const schemaUrl = schemaString("url");

  const schemaAuthor = schemaObject?.author;
  const schemaPublisher = schemaObject?.publisher;
  const schemaImage = schemaObject?.image;
  const schemaDatePublished = schemaString("datePublished");
  const schemaDateModified = schemaString("dateModified");

  const normalizedSchemaType = schemaType.toLowerCase();

  const schemaChecks: SchemaHealthCheck[] = [
    {
      id: "schema-present",
      label: "Schema present",
      passed: schemaPresent,
      required: true,
      detail: schemaPresent
        ? "JSON-LD schema object is present."
        : "Generate or add JSON-LD schema.",
    },
    {
      id: "schema-object",
      label: "Valid schema object",
      passed: schemaObject !== null,
      required: true,
      detail:
        schemaObject !== null
          ? "Schema is a valid object."
          : "Schema must be a JSON object, not an array.",
    },
    {
      id: "schema-context",
      label: "@context",
      passed:
        schemaContext === "https://schema.org" ||
        schemaContext === "http://schema.org",
      required: true,
      detail:
        schemaContext
          ? `Context: ${schemaContext}`
          : "Add https://schema.org as @context.",
    },
    {
      id: "schema-type",
      label: "@type",
      passed:
        normalizedSchemaType === "article" ||
        normalizedSchemaType === "newsarticle" ||
        normalizedSchemaType === "blogposting",
      required: true,
      detail:
        schemaType
          ? `Schema type: ${schemaType}`
          : "Use Article, NewsArticle, or BlogPosting.",
    },
    {
      id: "schema-headline",
      label: "Headline",
      passed:
        schemaHeadline.length > 0 &&
        (
          schemaHeadline.toLowerCase() ===
            title.toLowerCase() ||
          schemaHeadline.toLowerCase() ===
            metaTitle.toLowerCase()
        ),
      required: true,
      detail:
        !schemaHeadline
          ? "Add a schema headline."
          : schemaHeadline.toLowerCase() ===
                title.toLowerCase() ||
              schemaHeadline.toLowerCase() ===
                metaTitle.toLowerCase()
            ? "Headline matches title or meta title."
            : "Schema headline differs from title metadata.",
    },
    {
      id: "schema-description",
      label: "Description",
      passed:
        schemaDescription.length > 0 &&
        (
          schemaDescription.toLowerCase() ===
            metaDescription.toLowerCase() ||
          schemaDescription.toLowerCase() ===
            document.excerpt.trim().toLowerCase()
        ),
      required: true,
      detail:
        !schemaDescription
          ? "Add a schema description."
          : schemaDescription.toLowerCase() ===
                metaDescription.toLowerCase() ||
              schemaDescription.toLowerCase() ===
                document.excerpt.trim().toLowerCase()
            ? "Description matches article metadata."
            : "Schema description differs from metadata.",
    },
    {
      id: "schema-url",
      label: "Canonical URL consistency",
      passed:
        schemaUrl.length > 0 &&
        canonical.length > 0 &&
        schemaUrl.toLowerCase() === canonical.toLowerCase(),
      required: true,
      detail:
        !schemaUrl
          ? "Add the canonical URL as schema url."
          : schemaUrl.toLowerCase() ===
              canonical.toLowerCase()
            ? "Schema URL matches canonical URL."
            : "Schema URL does not match canonical URL.",
    },
    {
      id: "schema-author",
      label: "Author",
      passed:
        typeof schemaAuthor === "string" ||
        (
          schemaAuthor !== null &&
          typeof schemaAuthor === "object"
        ),
      required: false,
      detail:
        schemaAuthor
          ? "Author data is present."
          : "Add author data for stronger Article schema.",
    },
    {
      id: "schema-publisher",
      label: "Publisher",
      passed:
        schemaPublisher !== null &&
        typeof schemaPublisher === "object",
      required: false,
      detail:
        schemaPublisher
          ? "Publisher data is present."
          : "Add VenusRealm publisher data.",
    },
    {
      id: "schema-image",
      label: "Image",
      passed:
        typeof schemaImage === "string" ||
        Array.isArray(schemaImage) ||
        (
          schemaImage !== null &&
          typeof schemaImage === "object"
        ),
      required: false,
      detail:
        schemaImage
          ? "Schema image data is present."
          : "Add a representative article image.",
    },
    {
      id: "schema-date-published",
      label: "Date published",
      passed: schemaDatePublished.length > 0,
      required: false,
      detail:
        schemaDatePublished
          ? "datePublished is present."
          : "Add datePublished when publishing.",
    },
    {
      id: "schema-date-modified",
      label: "Date modified",
      passed: schemaDateModified.length > 0,
      required: false,
      detail:
        schemaDateModified
          ? "dateModified is present."
          : "Add dateModified for updated content.",
    },
  ];

  const schemaPassed = schemaChecks.filter(
    check => check.passed,
  ).length;

  const schemaRequiredChecks = schemaChecks.filter(
    check => check.required,
  );

  const schemaRequiredPassed =
    schemaRequiredChecks.filter(
      check => check.passed,
    ).length;

  const schemaOptionalChecks = schemaChecks.filter(
    check => !check.required,
  );

  const schemaOptionalPassed =
    schemaOptionalChecks.filter(
      check => check.passed,
    ).length;

  const schemaHealthScore = Math.round(
    (
      schemaRequiredPassed /
      Math.max(1, schemaRequiredChecks.length)
    ) * 80 +
    (
      schemaOptionalPassed /
      Math.max(1, schemaOptionalChecks.length)
    ) * 20,
  );

  const socialPreviewTitle =
    metaTitle ||
    title;

  const socialPreviewDescription =
    metaDescription ||
    document.excerpt.trim();

  const socialPreviewUrl =
    canonical ||
    (
      slug
        ? `https://venusrealm.net/${slug}`
        : ""
    );

  const socialPreviewImage =
    imageSeoRecords.find(image => image.src)?.src || "";

  const socialPreviewChecks: SocialPreviewCheck[] = [
    {
      id: "social-title",
      label: "Preview title",
      passed:
        socialPreviewTitle.length >= 30 &&
        socialPreviewTitle.length <= 70,
      detail:
        socialPreviewTitle.length >= 30 &&
        socialPreviewTitle.length <= 70
          ? "Title length is suitable for search and social previews."
          : `${socialPreviewTitle.length} characters; use 30–70.`,
    },
    {
      id: "social-description",
      label: "Preview description",
      passed:
        socialPreviewDescription.length >= 100 &&
        socialPreviewDescription.length <= 200,
      detail:
        socialPreviewDescription.length >= 100 &&
        socialPreviewDescription.length <= 200
          ? "Description length is suitable."
          : `${socialPreviewDescription.length} characters; use 100–200.`,
    },
    {
      id: "social-url",
      label: "Preview URL",
      passed:
        /^https:\/\/(?:www\.)?venusrealm\.net(?:\/|$)/i.test(
          socialPreviewUrl,
        ),
      detail:
        socialPreviewUrl
          ? "VenusRealm preview URL is available."
          : "Add a canonical URL or valid slug.",
    },
    {
      id: "social-image",
      label: "Preview image",
      passed: socialPreviewImage.length > 0,
      detail:
        socialPreviewImage
          ? "Article image is available for social cards."
          : "Add an image block for richer social previews.",
    },
    {
      id: "social-sharing",
      label: "Social sharing enabled",
      passed: document.socialSharing.enabled,
      detail:
        document.socialSharing.enabled
          ? "Social sharing is enabled."
          : "Enable social sharing for this article.",
    },
    {
      id: "social-platforms",
      label: "Sharing platforms",
      passed:
        document.socialSharing.enabled &&
        document.socialSharing.platforms.length > 0,
      detail:
        document.socialSharing.platforms.length > 0
          ? `${document.socialSharing.platforms.length} platforms selected.`
          : "Select at least one sharing platform.",
    },
    {
      id: "facebook-platform",
      label: "Facebook sharing",
      passed:
        !document.socialSharing.enabled ||
        document.socialSharing.platforms.includes(
          "facebook",
        ),
      detail:
        document.socialSharing.platforms.includes(
          "facebook",
        )
          ? "Facebook sharing is selected."
          : "Facebook is not selected.",
    },
    {
      id: "x-platform",
      label: "X sharing",
      passed:
        !document.socialSharing.enabled ||
        document.socialSharing.platforms.includes("x"),
      detail:
        document.socialSharing.platforms.includes("x")
          ? "X sharing is selected."
          : "X is not selected.",
    },
  ];

  const socialPreviewPassed =
    socialPreviewChecks.filter(
      check => check.passed,
    ).length;

  const socialPreviewScore = Math.round(
    (
      socialPreviewPassed /
      Math.max(1, socialPreviewChecks.length)
    ) * 100,
  );

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

  const publishChecklistItems: PublishChecklistItem[] = [
    {
      id: "title",
      label: "Article title",
      passed: title.length >= 10,
      required: true,
      detail:
        title.length >= 10
          ? "Title is ready."
          : "Add a clear article title.",
    },
    {
      id: "slug",
      label: "URL slug",
      passed:
        slug.length >= 5 &&
        /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug),
      required: true,
      detail:
        slug.length >= 5 &&
        /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)
          ? "Slug format is valid."
          : "Use a lowercase hyphenated slug.",
    },
    {
      id: "excerpt",
      label: "Article excerpt",
      passed: document.excerpt.trim().length >= 80,
      required: true,
      detail:
        document.excerpt.trim().length >= 80
          ? "Excerpt is ready."
          : "Add an excerpt of at least 80 characters.",
    },
    {
      id: "h1",
      label: "Single H1",
      passed: headings.counts[1] === 1,
      required: true,
      detail:
        headings.counts[1] === 1
          ? "Exactly one H1 found."
          : "Article must contain exactly one H1.",
    },
    {
      id: "meta-title",
      label: "Meta title",
      passed:
        metaTitle.length >= 30 &&
        metaTitle.length <= 60,
      required: true,
      detail:
        metaTitle.length >= 30 &&
        metaTitle.length <= 60
          ? "Meta title length is ready."
          : "Use 30–60 characters.",
    },
    {
      id: "meta-description",
      label: "Meta description",
      passed:
        metaDescription.length >= 120 &&
        metaDescription.length <= 160,
      required: true,
      detail:
        metaDescription.length >= 120 &&
        metaDescription.length <= 160
          ? "Meta description length is ready."
          : "Use 120–160 characters.",
    },
    {
      id: "focus-keyword",
      label: "Focus keyword",
      passed: normalizedKeyword.length > 0,
      required: true,
      detail:
        normalizedKeyword.length > 0
          ? "Focus keyword configured."
          : "Add a focus keyword.",
    },
    {
      id: "canonical",
      label: "Canonical URL",
      passed: /^https:\/\/(?:www\.)?venusrealm\.net(?:\/|$)/i.test(
        canonical,
      ),
      required: true,
      detail:
        /^https:\/\/(?:www\.)?venusrealm\.net(?:\/|$)/i.test(
          canonical,
        )
          ? "Canonical URL is valid."
          : "Add a valid HTTPS VenusRealm canonical URL.",
    },
    {
      id: "links",
      label: "Link validity",
      passed: links.invalid === 0,
      required: true,
      detail:
        links.invalid === 0
          ? "No invalid links detected."
          : `${links.invalid} invalid links detected.`,
    },
    {
      id: "image-alt",
      label: "Image ALT text",
      passed:
        images.length === 0 ||
        missingAltImages.length === 0,
      required: true,
      detail:
        images.length === 0
          ? "No image blocks to validate."
          : missingAltImages.length === 0
            ? "All image blocks include ALT text."
            : `${missingAltImages.length} images are missing ALT text.`,
    },
    {
      id: "risk-disclaimer",
      label: "Risk disclaimer",
      passed: hasRiskDisclaimer,
      required: true,
      detail:
        hasRiskDisclaimer
          ? "Risk wording detected."
          : "Add an educational financial-risk disclaimer.",
    },
    {
      id: "seo-score",
      label: "SEO score",
      passed: Math.min(seoScore, 100) >= 70,
      required: false,
      detail:
        Math.min(seoScore, 100) >= 70
          ? "SEO score is at least 70."
          : "Improve the SEO score to 70 or higher.",
    },
    {
      id: "readability",
      label: "Readability",
      passed: roundedReadabilityScore >= 50,
      required: false,
      detail:
        roundedReadabilityScore >= 50
          ? "Readability is acceptable."
          : "Simplify long sentences and paragraphs.",
    },
  ];

  const requiredPublishItems =
    publishChecklistItems.filter(item => item.required);

  const publishChecklist: PublishChecklist = {
    ready: requiredPublishItems.every(item => item.passed),
    passed: publishChecklistItems.filter(
      item => item.passed,
    ).length,
    total: publishChecklistItems.length,
    items: publishChecklistItems,
  };

  const passedChecks = checks.filter(
    check => check.passed,
  ).length;

  const contentScore = Math.round(
    (passedChecks / checks.length) * 100,
  );

  const publishReadinessScore = Math.round(
    (
      publishChecklist.passed /
      Math.max(1, publishChecklist.total)
    ) * 100,
  );

  const healthStatus = (
    score: number,
  ): SeoHealthCategory["status"] =>
    score >= 80
      ? "good"
      : score >= 60
        ? "warning"
        : "critical";

  const healthCategories: SeoHealthCategory[] = [
    {
      id: "seo",
      label: "SEO",
      score: Math.min(seoScore, 100),
      weight: 25,
      status: healthStatus(Math.min(seoScore, 100)),
    },
    {
      id: "content",
      label: "Content",
      score: contentScore,
      weight: 15,
      status: healthStatus(contentScore),
    },
    {
      id: "readability",
      label: "Readability",
      score: roundedReadabilityScore,
      weight: 10,
      status: healthStatus(roundedReadabilityScore),
    },
    {
      id: "images",
      label: "Image SEO",
      score: imageSeoScore,
      weight: 10,
      status: healthStatus(imageSeoScore),
    },
    {
      id: "schema",
      label: "Schema",
      score: schemaHealthScore,
      weight: 15,
      status: healthStatus(schemaHealthScore),
    },
    {
      id: "social",
      label: "Social",
      score: socialPreviewScore,
      weight: 10,
      status: healthStatus(socialPreviewScore),
    },
    {
      id: "publish",
      label: "Publish",
      score: publishReadinessScore,
      weight: 15,
      status: healthStatus(publishReadinessScore),
    },
  ];

  const advancedHealthScore = Math.round(
    healthCategories.reduce(
      (total, category) =>
        total +
        category.score * (category.weight / 100),
      0,
    ),
  );

  const advancedHealthGrade:
    AdvancedSeoHealthAnalysis["grade"] =
      advancedHealthScore >= 95
        ? "A+"
        : advancedHealthScore >= 90
          ? "A"
          : advancedHealthScore >= 80
            ? "B"
            : advancedHealthScore >= 70
              ? "C"
              : advancedHealthScore >= 60
                ? "D"
                : "F";

  const advancedHealthLabel:
    AdvancedSeoHealthAnalysis["label"] =
      advancedHealthScore >= 90
        ? "Excellent"
        : advancedHealthScore >= 80
          ? "Good"
          : advancedHealthScore >= 60
            ? "Improve"
            : "Critical";

  const healthIssueCandidates: SeoHealthPriorityIssue[] = [
    ...publishChecklist.items
      .filter(item => !item.passed && item.required)
      .map(item => ({
        id: `publish-${item.id}`,
        label: item.label,
        detail: item.detail,
        source: "Publish checklist",
        severity: "critical" as const,
      })),
    ...schemaChecks
      .filter(check => !check.passed && check.required)
      .map(check => ({
        id: `schema-${check.id}`,
        label: check.label,
        detail: check.detail,
        source: "Schema health",
        severity: "critical" as const,
      })),
    ...checks
      .filter(check => !check.passed)
      .map(check => ({
        id: `content-${check.id}`,
        label: check.label,
        detail: check.detail,
        source: "Content checker",
        severity:
          check.severity === "error"
            ? "critical" as const
            : "warning" as const,
      })),
    ...socialPreviewChecks
      .filter(check => !check.passed)
      .map(check => ({
        id: `social-${check.id}`,
        label: check.label,
        detail: check.detail,
        source: "Social preview",
        severity: "warning" as const,
      })),
  ];

  if (imageIssueCount > 0) {
    healthIssueCandidates.push({
      id: "image-seo-issues",
      label: "Image SEO issues",
      detail: `${imageIssueCount} image issues detected.`,
      source: "Image SEO",
      severity:
        missingAltImages.length > 0 ||
        missingSourceImages > 0
          ? "critical"
          : "warning",
    });
  }

  const uniqueHealthIssues = Array.from(
    new Map(
      healthIssueCandidates.map(issue => [
        `${issue.label}|${issue.detail}`,
        issue,
      ]),
    ).values(),
  );

  const criticalHealthIssues = uniqueHealthIssues.filter(
    issue => issue.severity === "critical",
  );

  const warningHealthIssues = uniqueHealthIssues.filter(
    issue => issue.severity === "warning",
  );

  const priorityHealthIssues = [
    ...criticalHealthIssues,
    ...warningHealthIssues,
  ].slice(0, 5);

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
    publishChecklist,
    imageSeo: {
      score: imageSeoScore,
      total: images.length,
      missingAlt: missingAltImages.length,
      missingSource: missingSourceImages,
      missingDimensions: missingDimensionImages,
      missingCaption: missingCaptionImages,
      externalSources: externalImageSources,
      largeDimensions: largeDimensionImages,
      issueCount: imageIssueCount,
      records: imageSeoRecords,
    },
    schemaHealth: {
      score: schemaHealthScore,
      present: schemaPresent,
      validObject: schemaObject !== null,
      schemaType,
      passed: schemaPassed,
      total: schemaChecks.length,
      checks: schemaChecks,
    },
    socialPreview: {
      score: socialPreviewScore,
      title: socialPreviewTitle,
      description: socialPreviewDescription,
      url: socialPreviewUrl,
      image: socialPreviewImage,
      sharingEnabled: document.socialSharing.enabled,
      platforms: document.socialSharing.platforms,
      passed: socialPreviewPassed,
      total: socialPreviewChecks.length,
      checks: socialPreviewChecks,
    },
    advancedHealth: {
      score: advancedHealthScore,
      grade: advancedHealthGrade,
      label: advancedHealthLabel,
      ready:
        publishChecklist.ready &&
        criticalHealthIssues.length === 0 &&
        advancedHealthScore >= 80,
      criticalCount: criticalHealthIssues.length,
      warningCount: warningHealthIssues.length,
      categories: healthCategories,
      priorityIssues: priorityHealthIssues,
    },
  };
}
