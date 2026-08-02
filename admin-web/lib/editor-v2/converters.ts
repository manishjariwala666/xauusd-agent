import type {
  CmsBlock,
  CmsDocument,
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

export function cmsApiDetailToDocument(
  content: CmsApiContentDetail,
): CmsDocument {
  const body = String(content.body || "");
  const structured = extractStructuredDocument(body);

  if (structured) {
    return {
      ...structured,
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
    blocks: [
      {
        id: `legacy-${content.id}`,
        type: "paragraph" as const,
        html: body,
      },
    ],
    seo: {
      metaTitle: "",
      metaDescription: "",
      focusKeyword: "",
      canonicalUrl: "",
      robotsIndex: false,
      robotsFollow: false,
      schemaJsonLd: null,
    },
    scheduledAt: content.scheduled_at ?? null,
    publishedAt: content.published_at ?? null,
    createdAt: content.created_at ?? null,
    updatedAt: content.updated_at ?? null,
  };

  return document;
}
