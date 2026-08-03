import type {
  CmsBlock,
    CmsDocument,
    CmsSocialPlatform
} from "./document-types";

export type CmsApiPayload = {
  title: string;
  slug: string;
  excerpt: string;
  body: string;
  category_id: number | null;
  subcategory: string;
  status: "draft";
  scheduled_at: string | null;
  published_at: string | null;
};

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderBlock(block: CmsBlock): string {
  switch (block.type) {
    case "paragraph":
      return `<div data-cms-block="paragraph">${block.html}</div>`;

    case "heading":
      return `<h${block.level}>${escapeHtml(block.text)}</h${block.level}>`;

    case "image": {
      if (!block.src) return "";

      const image = [
        `<img src="${escapeHtml(block.src)}"`,
        ` alt="${escapeHtml(block.alt)}"`,
        block.width ? ` width="${block.width}"` : "",
        block.height ? ` height="${block.height}"` : "",
        " />",
      ].join("");

      const linkedImage = block.linkUrl
        ? `<a href="${escapeHtml(block.linkUrl)}">${image}</a>`
        : image;

      return [
        `<figure data-cms-block="image" data-alignment="${block.alignment}">`,
        linkedImage,
        block.caption
          ? `<figcaption>${escapeHtml(block.caption)}</figcaption>`
          : "",
        "</figure>",
      ].join("");
    }

    case "gallery":
      return [
        `<div data-cms-block="gallery"`,
        ` data-media-ids="${escapeHtml(block.mediaIds.join(","))}"`,
        ` data-columns="${block.columns}"`,
        ` data-gap="${block.gap}"`,
        ` data-lightbox="${block.lightbox}"`,
        ` data-show-captions="${block.showCaptions}"></div>`,
      ].join("");

    case "table":
      return `<div data-cms-block="table">${block.html}</div>`;

    case "quote":
      return [
        "<blockquote>",
        block.html,
        block.citation
          ? `<cite>${escapeHtml(block.citation)}</cite>`
          : "",
        "</blockquote>",
      ].join("");

    case "code":
      return [
        `<pre data-language="${escapeHtml(block.language)}"><code>`,
        escapeHtml(block.code),
        "</code></pre>",
      ].join("");

    case "button":
      return [
        `<p data-cms-block="button" data-alignment="${block.alignment}">`,
        `<a href="${escapeHtml(block.url)}"`,
        ` class="cms-button-${block.style}">`,
        escapeHtml(block.label),
        "</a></p>",
      ].join("");

    case "divider":
      return `<hr class="divider-${block.style}" />`;

    case "accordion":
      return [
        `<div data-cms-block="accordion">`,
        ...block.items.map(item => [
          "<details>",
          `<summary>${escapeHtml(item.title)}</summary>`,
          `<div>${item.html}</div>`,
          "</details>",
        ].join("")),
        "</div>",
      ].join("");

    case "youtube":
      return [
        `<div data-cms-block="youtube">`,
        `<a href="${escapeHtml(block.url)}">`,
        escapeHtml(block.title || block.url),
        "</a></div>",
      ].join("");
  }
}

export function cmsDocumentToHtml(
  document: CmsDocument,
): string {
  const structuredDocument = encodeURIComponent(
    JSON.stringify(document),
  );

  const renderedBlocks = document.blocks
    .map(renderBlock)
    .filter(Boolean)
    .join("\n");

  return [
    `<!--venusrealm-cms-v2:${structuredDocument}-->`,
    renderedBlocks,
  ].join("\n");
}

export function cmsDocumentToApiPayload(
  document: CmsDocument,
): CmsApiPayload {
  return {
    title: document.title.trim(),
    slug: document.slug.trim(),
    excerpt: document.excerpt.trim(),
    body: cmsDocumentToHtml(document),
    category_id: document.categoryId,
    subcategory: "",
    status: "draft",
    scheduled_at: null,
    published_at: null,
  };
}

function createImportedBlockId(
  type: string,
  index: number,
): string {
  return `imported-${type}-${index}-${Date.now()}`;
}

function stripHtmlTags(value: string): string {
  return value
    .replace(/<br\s*\/?>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"')
    .replace(/&#039;/gi, "'")
    .replace(/\s+/g, " ")
    .trim();
}

function legacyHtmlToBlocks(
  body: string,
): CmsDocument["blocks"] {
  const normalized = body.trim();

  if (!normalized) {
    return [
      {
        id: createImportedBlockId("paragraph", 0),
        type: "paragraph",
        html: "<p></p>",
      },
    ];
  }

  const tokenPattern =
    /<(h[1-6]|table|blockquote|ul|ol)\b[^>]*>[\s\S]*?<\/\1>|<hr\b[^>]*\/?\s*>/gi;

  const blocks: CmsDocument["blocks"] = [];
  let cursor = 0;
  let index = 0;
  let match: RegExpExecArray | null;

  function pushParagraph(html: string) {
    const clean = html.trim();

    if (!clean || !stripHtmlTags(clean)) return;

    blocks.push({
      id: createImportedBlockId("paragraph", index++),
      type: "paragraph",
      html: clean,
    });
  }

  while ((match = tokenPattern.exec(normalized)) !== null) {
    pushParagraph(normalized.slice(cursor, match.index));

    const html = match[0];
    const tag = String(match[1] || "hr").toLowerCase();

    if (/^h[1-6]$/.test(tag)) {
      blocks.push({
        id: createImportedBlockId("heading", index++),
        type: "heading",
        level: Number(tag.slice(1)) as 1 | 2 | 3 | 4 | 5 | 6,
        text: stripHtmlTags(html),
      });
    } else if (tag === "table") {
      blocks.push({
        id: createImportedBlockId("table", index++),
        type: "table",
        html,
      });
    } else if (tag === "blockquote") {
      blocks.push({
        id: createImportedBlockId("quote", index++),
        type: "quote",
        html,
        citation: "",
      });
    } else {
      blocks.push({
        id: createImportedBlockId("divider", index++),
        type: "divider",
        style: "solid",
      });
    }

    cursor = match.index + html.length;
  }

  pushParagraph(normalized.slice(cursor));

  return blocks.length
    ? blocks
    : [
        {
          id: createImportedBlockId("paragraph", 0),
          type: "paragraph",
          html: normalized,
        },
      ];
}

export type CmsApiContentDetail = {
  id: number;
  title?: string | null;
  slug?: string | null;
  excerpt?: string | null;
  body?: string | null;
  category_id?: number | null;
  featured_media_id?: number | null;
  status?: string | null;
  scheduled_at?: string | null;
  published_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

function blockFingerprint(block: CmsDocument["blocks"][number]): string {
  return JSON.stringify(block, (key, value) =>
    key === "id" ? undefined : value,
  );
}

function expandHtmlCodeBlocks(
  blocks: CmsDocument["blocks"],
): CmsDocument["blocks"] {
  return blocks.flatMap(block => {
    if (block.type !== "code") {
      return [block];
    }

    const source = String(block.code || "").trim();

    const containsArticleHtml =
      /<(?:h[1-6]|p|ul|ol|li|table|thead|tbody|tr|th|td|blockquote|hr|strong|em)\b/i
        .test(source);

    if (!containsArticleHtml) {
      return [block];
    }

    return legacyHtmlToBlocks(source);
  });
}

function removeExactDuplicateBlocks(
  blocks: CmsDocument["blocks"],
): CmsDocument["blocks"] {
  const seen = new Set<string>();

  return blocks.filter(block => {
    const fingerprint = blockFingerprint(block);

    if (seen.has(fingerprint)) {
      return false;
    }

    seen.add(fingerprint);
    return true;
  });
}

function extractStructuredDocument(
  body: string,
): CmsDocument | null {
  const match = body.match(
    /<!--venusrealm-cms-v2:([^]*?)-->/,
  );

  if (!match?.[1]) return null;

  try {
    return JSON.parse(
      decodeURIComponent(match[1]),
    ) as CmsDocument;
  } catch {
    return null;
  }
}

export function normalizeCmsDocument(
  document: CmsDocument,
): CmsDocument {
  return {
    ...document,
    blocks: removeExactDuplicateBlocks(
      expandHtmlCodeBlocks(document.blocks || []),
    ),
    socialSharing: {
      enabled: document.socialSharing?.enabled ?? false,
      platforms:
        document.socialSharing?.platforms?.length
          ? document.socialSharing.platforms
          : [
              "whatsapp",
              "telegram",
              "facebook",
              "x",
              "linkedin",
              "copy",
            ],
    },
    relatedPosts: {
      enabled: document.relatedPosts?.enabled ?? false,
      heading:
        document.relatedPosts?.heading?.trim() ||
        "Related Posts",
      items: document.relatedPosts?.items || [],
    },
    toc: {
      enabled: document.toc?.enabled ?? false,
      title:
        document.toc?.title?.trim() ||
        "Table of Contents",
      maxDepth:
        document.toc?.maxDepth === 2 ||
        document.toc?.maxDepth === 3 ||
        document.toc?.maxDepth === 4 ||
        document.toc?.maxDepth === 5 ||
        document.toc?.maxDepth === 6
          ? document.toc.maxDepth
          : 3,
    },
  };
}


export function cmsApiDetailToDocument(
  content: CmsApiContentDetail,
): CmsDocument {
  const body = String(content.body || "");
  const structured = extractStructuredDocument(body);

  if (structured) {
    return {
      ...structured,
      blocks: normalizeCmsDocument(structured).blocks,
      toc: normalizeCmsDocument(structured).toc,
      socialSharing:
        normalizeCmsDocument(structured).socialSharing,
      relatedPosts:
        normalizeCmsDocument(structured).relatedPosts,
      id: content.id,
      title: String(content.title || structured.title || ""),
      slug: String(content.slug || structured.slug || ""),
      excerpt: String(content.excerpt || structured.excerpt || ""),
      categoryId:
        content.category_id ?? structured.categoryId ?? null,
      featuredMediaId:
        content.featured_media_id ??
        structured.featuredMediaId ??
        null,
      status:
        content.status === "published"
          ? "published"
          : content.status === "scheduled"
            ? "scheduled"
            : content.status === "trash"
              ? "trash"
              : "draft",
      scheduledAt:
        content.scheduled_at ?? structured.scheduledAt ?? null,
      publishedAt:
        content.published_at ?? structured.publishedAt ?? null,
      createdAt:
        content.created_at ?? structured.createdAt ?? null,
      updatedAt:
        content.updated_at ?? structured.updatedAt ?? null,
    };
  }

  const document = {
    id: content.id,
    title: String(content.title || ""),
    slug: String(content.slug || ""),
    excerpt: String(content.excerpt || ""),
    status: "draft" as const,
    categoryId: content.category_id ?? null,
    tags: [],
    featuredMediaId: content.featured_media_id ?? null,
    blocks: legacyHtmlToBlocks(body),
    seo: {
      metaTitle: "",
      metaDescription: "",
      focusKeyword: "",
      canonicalUrl: "",
      robotsIndex: false,
      robotsFollow: false,
      schemaJsonLd: null,
    },
    socialSharing: {
      enabled: false,
      platforms: [
        "whatsapp",
        "telegram",
        "facebook",
        "x",
        "linkedin",
        "copy",
      ] as CmsSocialPlatform[],
    },
    relatedPosts: {
      enabled: false,
      heading: "Related Posts",
      items: [],
    },
    toc: {
      enabled: false,
      title: "Table of Contents",
      maxDepth: 3 as const,
    },
    scheduledAt: content.scheduled_at ?? null,
    publishedAt: content.published_at ?? null,
    createdAt: content.created_at ?? null,
    updatedAt: content.updated_at ?? null,
  };

  return document;
}
