"use client";

import { useState } from "react";

import type {
  CmsBlock,
  CmsDocument,
} from "@/lib/editor-v2/document-types";

type DocumentPreviewProps = {
  document: CmsDocument;
  onClose: () => void;
};

function decodeHtmlEntities(value: string): string {
  if (typeof window === "undefined" || !value) {
    return value;
  }

  const textarea = window.document.createElement("textarea");
  textarea.innerHTML = value;

  return textarea.value;
}

function normalizePreviewHtml(value: string): string {
  let html = String(value || "").trim();

  for (let attempt = 0; attempt < 2; attempt += 1) {
    if (
      !html.includes("&lt;") &&
      !html.includes("&gt;") &&
      !html.includes("&amp;")
    ) {
      break;
    }

    html = decodeHtmlEntities(html);
  }

  html = html
    .replace(/^```(?:html)?\s*/i, "")
    .replace(/\s*```$/i, "")
    .trim();

  const codeWrapper = html.match(
    /^<pre[^>]*>\s*<code[^>]*>([\s\S]*?)<\/code>\s*<\/pre>$/i,
  );

  if (codeWrapper?.[1]) {
    html = decodeHtmlEntities(codeWrapper[1]);
  }

  return html;
}


function looksLikeHtml(value: string): boolean {
  const html = String(value || "").trim();

  return /<\/?(?:html|body|main|article|section|aside|nav|header|footer|div|span|h[1-6]|p|ul|ol|li|table|thead|tbody|tr|th|td|blockquote|figure|figcaption|img|a|hr|br|details|summary)\b[^>]*>/i.test(
    html,
  );
}

function sanitizePreviewHtml(value: string): string {
  return normalizePreviewHtml(value)
    .replace(
      /<(script|iframe|object|embed|form|style)\b[^>]*>[\s\S]*?<\/\1>/gi,
      "",
    )
    .replace(
      /<(script|iframe|object|embed|form|style)\b[^>]*\/?>/gi,
      "",
    )
    .replace(
      /\s+on[a-z]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)/gi,
      "",
    )
    .replace(
      /\s+(href|src)\s*=\s*(["'])\s*javascript:[\s\S]*?\2/gi,
      ' $1="#"',
    );
}


type TocHeading = {
  id: string;
  level: 2 | 3 | 4 | 5 | 6;
  text: string;
};

type TocNode = TocHeading & {
  children: TocNode[];
};

function stripHtmlText(value: string): string {
  return normalizePreviewHtml(value)
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}


const AUTO_TOC_IGNORED_HEADINGS = new Set([
  "table of contents",
  "contents",
  "quick summary",
  "summary",
  "overview",
]);

function normalizeHeadingLabel(value: string): string {
  return stripHtmlText(value)
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

function isIgnoredTocHeading(value: string): boolean {
  return AUTO_TOC_IGNORED_HEADINGS.has(
    normalizeHeadingLabel(value),
  );
}

function stripManualTocFromHtml(value: string): string {
  let html = normalizePreviewHtml(value);

  /*
   * Remove a manual TOC heading followed by a typical TOC container.
   * Supported patterns:
   *   <h2>Table of Contents</h2><nav>...</nav>
   *   <h2>Table of Contents</h2><ol>...</ol>
   *   <h2>Contents</h2><ul>...</ul>
   */
  html = html.replace(
    /<h([2-6])\b[^>]*>\s*(?:table\s+of\s+contents|contents)\s*<\/h\1>\s*(?:<nav\b[^>]*>[\s\S]*?<\/nav>|<ol\b[^>]*>[\s\S]*?<\/ol>|<ul\b[^>]*>[\s\S]*?<\/ul>)/gi,
    "",
  );

  /*
   * Also remove a standalone manual TOC nav when it is explicitly labelled.
   */
  html = html.replace(
    /<nav\b[^>]*(?:aria-label\s*=\s*["']table of contents["']|class\s*=\s*["'][^"']*\b(?:toc|table-of-contents)\b[^"']*["'])[^>]*>[\s\S]*?<\/nav>/gi,
    "",
  );

  return html.trim();
}

function slugifyHeading(value: string): string {
  return stripHtmlText(value)
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 120) || "section";
}

function extractExplicitHeadingId(
  attributes: string,
): string | null {
  const match = attributes.match(
    /\bid\s*=\s*(["'])([^"']+)\1/i,
  );

  const candidate = match?.[2]?.trim();

  if (
    !candidate ||
    !/^[A-Za-z][A-Za-z0-9_:.-]*$/.test(candidate)
  ) {
    return null;
  }

  return candidate;
}

function collectTocHeadings(
  document: CmsDocument,
): TocHeading[] {
  const headings: Array<{
    level: 2 | 3 | 4 | 5 | 6;
    text: string;
    preferredId?: string | null;
  }> = [];

  for (const block of document.blocks) {
    if (
      block.type === "heading" &&
      block.level >= 2 &&
      block.level <= document.toc.maxDepth
    ) {
      const text = block.text.trim();

      if (text && !isIgnoredTocHeading(text)) {
        headings.push({
          level: block.level as 2 | 3 | 4 | 5 | 6,
          text,
        });
      }

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
        /<h([2-6])\b([^>]*)>([\s\S]*?)<\/h\1>/gi;
      const htmlForToc = document.toc.enabled
        ? stripManualTocFromHtml(block.code)
        : normalizePreviewHtml(block.code);

      let match: RegExpExecArray | null;

      while ((match = pattern.exec(htmlForToc)) !== null) {
        const level = Number(match[1]) as
          | 2 | 3 | 4 | 5 | 6;

        if (level > document.toc.maxDepth) continue;

        const label = stripHtmlText(match[3]);

        if (!label || isIgnoredTocHeading(label)) continue;

        headings.push({
          level,
          text: label,
          preferredId: extractExplicitHeadingId(match[2]),
        });
      }
    }
  }

  const used = new Set<string>();

  return headings.map(heading => {
    const base =
      heading.preferredId || slugifyHeading(heading.text);

    let id = base;
    let suffix = 2;

    while (used.has(id)) {
      id = `${base}-${suffix}`;
      suffix += 1;
    }

    used.add(id);

    return {
      id,
      level: heading.level,
      text: heading.text,
    };
  });
}

function buildTocTree(headings: TocHeading[]): TocNode[] {
  const roots: TocNode[] = [];
  const stack: TocNode[] = [];

  for (const heading of headings) {
    const node: TocNode = {
      ...heading,
      children: [],
    };

    while (
      stack.length &&
      stack[stack.length - 1].level >= node.level
    ) {
      stack.pop();
    }

    if (stack.length) {
      stack[stack.length - 1].children.push(node);
    } else {
      roots.push(node);
    }

    stack.push(node);
  }

  return roots;
}

function escapeHtmlAttribute(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function applyHeadingIdsToImportedHtml(
  html: string,
  headings: TocHeading[],
  cursor: { value: number },
  maxDepth: number,
): string {
  return stripManualTocFromHtml(html).replace(
    /<h([2-6])\b([^>]*)>([\s\S]*?)<\/h\1>/gi,
    (full, rawLevel: string, attributes: string, inner: string) => {
      const level = Number(rawLevel);

      if (
        level > maxDepth ||
        isIgnoredTocHeading(inner)
      ) {
        return full;
      }

      const heading = headings[cursor.value];

      if (!heading) return full;

      cursor.value += 1;

      const cleanAttributes = attributes.replace(
        /\s+id\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)/i,
        "",
      );

      return `<h${level}${cleanAttributes} id="${escapeHtmlAttribute(
        heading.id,
      )}">${inner}</h${level}>`;
    },
  );
}

function tocTreeToHtml(nodes: TocNode[]): string {
  if (!nodes.length) return "";

  return [
    "<ol>",
    ...nodes.map(node =>
      [
        "<li>",
        `<a href="#${escapeHtmlAttribute(node.id)}">${escapeHtmlAttribute(node.text)}</a>`,
        tocTreeToHtml(node.children),
        "</li>",
      ].join(""),
    ),
    "</ol>",
  ].join("");
}

function renderSourceToc(
  document: CmsDocument,
  headings: TocHeading[],
): string {
  if (!document.toc.enabled || !headings.length) {
    return "";
  }

  return [
    '<nav aria-label="Table of contents">',
    `<h2>${escapeHtmlAttribute(
      document.toc.title || "Table of Contents",
    )}</h2>`,
    tocTreeToHtml(buildTocTree(headings)),
    "</nav>",
  ].join("\n");
}

function documentSourceHtml(document: CmsDocument): string {
  const headings = collectTocHeadings(document);
  const cursor = { value: 0 };

  const renderedBlocks = document.blocks
    .map(block => {
      switch (block.type) {
        case "paragraph":
        case "table":
          return normalizePreviewHtml(block.html);

        case "heading": {
          if (
            block.level >= 2 &&
            block.level <= document.toc.maxDepth
          ) {
            const heading = headings[cursor.value];

            if (heading) {
              cursor.value += 1;

              return `<h${block.level} id="${escapeHtmlAttribute(
                heading.id,
              )}">${escapeHtmlAttribute(
                block.text,
              )}</h${block.level}>`;
            }
          }

          return `<h${block.level}>${escapeHtmlAttribute(
            block.text,
          )}</h${block.level}>`;
        }

        case "quote":
          return `<blockquote>${normalizePreviewHtml(block.html)}</blockquote>`;

        case "image":
          return block.src
            ? `<img src="${escapeHtmlAttribute(
                block.src,
              )}" alt="${escapeHtmlAttribute(block.alt)}" />`
            : "";

        case "divider":
          return "<hr />";

        case "button":
          return `<a href="${escapeHtmlAttribute(
            block.url,
          )}">${escapeHtmlAttribute(block.label)}</a>`;

        case "code":
          return (
            block.language === "html" ||
            looksLikeHtml(block.code)
          )
            ? applyHeadingIdsToImportedHtml(
                block.code,
                headings,
                cursor,
                document.toc.maxDepth,
              )
            : `<pre><code>${escapeHtmlAttribute(
                block.code,
              )}</code></pre>`;

        case "accordion":
          return block.items
            .map(
              item =>
                `<details><summary>${escapeHtmlAttribute(
                  item.title,
                )}</summary>${normalizePreviewHtml(
                  item.html,
                )}</details>`,
            )
            .join("\n");

        case "youtube":
          return `<a href="${escapeHtmlAttribute(
            block.url,
          )}">${escapeHtmlAttribute(
            block.title || block.url,
          )}</a>`;

        case "gallery":
          return `<!-- Gallery: ${block.mediaIds.length} images -->`;
      }
    })
    .filter(Boolean)
    .join("\n\n");

  return [
    renderSourceToc(document, headings),
    renderedBlocks,
  ]
    .filter(Boolean)
    .join("\n\n");
}

function PreviewBlock({
  block,
  headingId,
  importedHtml,
}: {
  block: CmsBlock;
  headingId?: string;
  importedHtml?: string;
}) {
  switch (block.type) {
    case "paragraph":
      return (
        <div
          className="studio-v2-preview-richtext"
          dangerouslySetInnerHTML={{
            __html: normalizePreviewHtml(block.html),
          }}
        />
      );

    case "heading": {
      const HeadingTag =
        `h${block.level}` as keyof React.JSX.IntrinsicElements;

      return (
        <HeadingTag id={headingId}>
          {block.text || "Untitled heading"}
        </HeadingTag>
      );
    }

    case "image":
      return block.src ? (
        <figure className={`studio-v2-preview-image align-${block.alignment}`}>
          <img
            src={block.src}
            alt={block.alt}
            style={{
              width: block.width ? `${block.width}px` : undefined,
              height: block.height ? `${block.height}px` : undefined,
            }}
          />

          {block.caption ? (
            <figcaption>{block.caption}</figcaption>
          ) : null}
        </figure>
      ) : null;

    case "table":
      return (
        <div
          className="studio-v2-preview-table"
          dangerouslySetInnerHTML={{
            __html: normalizePreviewHtml(block.html),
          }}
        />
      );

    case "quote":
      return (
        <blockquote>
          <div dangerouslySetInnerHTML={{
            __html: normalizePreviewHtml(block.html),
          }} />
          {block.citation ? <cite>{block.citation}</cite> : null}
        </blockquote>
      );

    case "code":
      if (
        block.language === "html" ||
        looksLikeHtml(block.code)
      ) {
        return (
          <div
            className="studio-v2-preview-richtext studio-v2-preview-custom-html"
            dangerouslySetInnerHTML={{
              __html:
                importedHtml ??
                sanitizePreviewHtml(block.code),
            }}
          />
        );
      }

      return (
        <pre>
          <code>{block.code}</code>
        </pre>
      );

    case "button":
      return (
        <div className={`studio-v2-preview-button align-${block.alignment}`}>
          <a
            href={block.url || "#"}
            className={`preview-button-${block.style}`}
            onClick={event => event.preventDefault()}
          >
            {block.label}
          </a>
        </div>
      );

    case "divider":
      return <hr className={`divider-${block.style}`} />;

    case "accordion":
      return (
        <div className="studio-v2-preview-accordion">
          {block.items.map(item => (
            <details key={item.id}>
              <summary>{item.title}</summary>
              <div dangerouslySetInnerHTML={{ __html: item.html }} />
            </details>
          ))}
        </div>
      );

    case "youtube": {
      const videoId = (() => {
        try {
          const url = new URL(block.url);

          if (url.hostname.includes("youtu.be")) {
            return url.pathname.replace("/", "");
          }

          if (url.hostname.includes("youtube.com")) {
            return (
              url.searchParams.get("v") ||
              url.pathname.split("/").filter(Boolean).at(-1) ||
              ""
            );
          }
        } catch {
          return "";
        }

        return "";
      })();

      return videoId ? (
        <a
          href={block.url}
          target="_blank"
          rel="noopener noreferrer"
          className="studio-v2-preview-youtube"
        >
          <img
            src={`https://img.youtube.com/vi/${videoId}/hqdefault.jpg`}
            alt={block.title || "YouTube video thumbnail"}
            loading="lazy"
            decoding="async"
          />

          <span className="studio-v2-preview-youtube-play" aria-hidden="true">
            ▶
          </span>

          <span className="studio-v2-preview-youtube-title">
            {block.title || "Watch on YouTube"}
          </span>
        </a>
      ) : (
        <div className="studio-v2-preview-placeholder">
          YouTube video URL required
        </div>
      );
    }

    case "gallery":
      return (
        <div className="studio-v2-preview-placeholder">
          Gallery block · {block.mediaIds.length} images · {block.columns} columns
        </div>
      );
  }
}


function TocList({
  nodes,
  onNavigate,
}: {
  nodes: TocNode[];
  onNavigate: (id: string) => void;
}) {
  if (!nodes.length) return null;

  return (
    <ol>
      {nodes.map(node => (
        <li key={node.id}>
          <a
            href={`#${node.id}`}
            onClick={event => {
              event.preventDefault();
              onNavigate(node.id);
            }}
          >
            {node.text}
          </a>

          {node.children.length ? (
            <TocList
              nodes={node.children}
              onNavigate={onNavigate}
            />
          ) : null}
        </li>
      ))}
    </ol>
  );
}

export function DocumentPreview({
  document,
  onClose,
}: DocumentPreviewProps) {
  const [mode, setMode] = useState<"visual" | "source">("visual");
  const headings = collectTocHeadings(document);
  const tocTree = buildTocTree(headings);
  const sourceHtml = documentSourceHtml(document);

  function navigateToHeading(id: string) {
    const target = window.document.getElementById(id);

    target?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  const visualHeadingCursor = { value: 0 };

  return (
    <div
      className="studio-v2-preview-backdrop"
      role="presentation"
      onMouseDown={event => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="studio-v2-preview-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="studio-preview-title"
      >
        <header className="studio-v2-preview-header">
          <div>
            <span className="section-kicker">DRAFT PREVIEW</span>
            <h2 id="studio-preview-title">
              {document.title || "Untitled article"}
            </h2>
          </div>

          <div className="studio-v2-preview-actions">
            <div
              className="studio-v2-preview-mode"
              role="group"
              aria-label="Preview mode"
            >
              <button
                type="button"
                className={mode === "visual" ? "active" : ""}
                onClick={() => setMode("visual")}
              >
                Visual
              </button>

              <button
                type="button"
                className={mode === "source" ? "active" : ""}
                onClick={() => setMode("source")}
              >
                Source
              </button>
            </div>

            <button
              type="button"
              className="secondary-button"
              onClick={onClose}
            >
              Close preview
            </button>
          </div>
        </header>

        {mode === "visual" ? (
          <article className="studio-v2-preview-article">
            {document.excerpt ? (
              <p className="studio-v2-preview-excerpt">
                {document.excerpt}
              </p>
            ) : null}

            {document.toc.enabled && headings.length > 0 ? (
              <nav
                className="studio-v2-preview-toc"
                aria-label="Table of contents"
              >
                <h2>
                  {document.toc.title ||
                    "Table of Contents"}
                </h2>

                <TocList
                  nodes={tocTree}
                  onNavigate={navigateToHeading}
                />
              </nav>
            ) : null}

            {document.blocks.map(block => {
              let headingId: string | undefined;
              let importedHtml: string | undefined;

              if (
                block.type === "heading" &&
                block.level >= 2 &&
                block.level <= document.toc.maxDepth
              ) {
                headingId =
                  headings[visualHeadingCursor.value]?.id;

                if (headingId) {
                  visualHeadingCursor.value += 1;
                }
              }

              if (
                block.type === "code" &&
                (
                  block.language === "html" ||
                  looksLikeHtml(block.code)
                )
              ) {
                importedHtml = sanitizePreviewHtml(
                  applyHeadingIdsToImportedHtml(
                    document.toc.enabled
                      ? stripManualTocFromHtml(block.code)
                      : block.code,
                    headings,
                    visualHeadingCursor,
                    document.toc.maxDepth,
                  ),
                );
              }

              return (
                <PreviewBlock
                  key={block.id}
                  block={block}
                  headingId={headingId}
                  importedHtml={importedHtml}
                />
              );
            })}

            {document.socialSharing.enabled &&
            document.socialSharing.platforms.length > 0 ? (
              <section className="studio-v2-preview-sharing">
                <h3>Share this article</h3>

                <div>
                  {document.socialSharing.platforms.map(platform => (
                    <button
                      key={platform}
                      type="button"
                      onClick={() => undefined}
                    >
                      {platform === "x"
                        ? "X"
                        : platform === "copy"
                          ? "Copy Link"
                          : platform.charAt(0).toUpperCase() +
                            platform.slice(1)}
                    </button>
                  ))}
                </div>
              </section>
            ) : null}

            {document.relatedPosts.enabled &&
            document.relatedPosts.items.length > 0 ? (
              <section className="studio-v2-preview-related">
                <h2>
                  {document.relatedPosts.heading ||
                    "Related Posts"}
                </h2>

                <div className="studio-v2-preview-related-grid">
                  {document.relatedPosts.items.map(item => (
                    <article key={item.id}>
                      <h3>{item.title || "Untitled related post"}</h3>

                      {item.excerpt ? <p>{item.excerpt}</p> : null}

                      <a
                        href={item.url || "#"}
                        onClick={event => event.preventDefault()}
                      >
                        Read article
                      </a>
                    </article>
                  ))}
                </div>
              </section>
            ) : null}
          </article>
        ) : (
          <pre className="studio-v2-preview-source">
            <code>{sourceHtml}</code>
          </pre>
        )}
      </section>
    </div>
  );
}
