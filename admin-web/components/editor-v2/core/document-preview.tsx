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

function documentSourceHtml(document: CmsDocument): string {
  return document.blocks
    .map(block => {
      switch (block.type) {
        case "paragraph":
        case "table":
          return normalizePreviewHtml(block.html);

        case "heading":
          return `<h${block.level}>${block.text}</h${block.level}>`;

        case "quote":
          return `<blockquote>${normalizePreviewHtml(block.html)}</blockquote>`;

        case "image":
          return block.src
            ? `<img src="${block.src}" alt="${block.alt}" />`
            : "";

        case "divider":
          return "<hr />";

        case "button":
          return `<a href="${block.url}">${block.label}</a>`;

        case "code":
          return `<pre><code>${block.code}</code></pre>`;

        case "accordion":
          return block.items
            .map(
              item =>
                `<details><summary>${item.title}</summary>${normalizePreviewHtml(item.html)}</details>`,
            )
            .join("\n");

        case "youtube":
          return `<a href="${block.url}">${block.title || block.url}</a>`;

        case "gallery":
          return `<!-- Gallery: ${block.mediaIds.length} images -->`;
      }
    })
    .filter(Boolean)
    .join("\n\n");
}

function PreviewBlock({ block }: { block: CmsBlock }) {
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

      return <HeadingTag>{block.text || "Untitled heading"}</HeadingTag>;
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

    case "youtube":
      return (
        <div className="studio-v2-preview-placeholder">
          YouTube: {block.title || block.url || "Video URL required"}
        </div>
      );

    case "gallery":
      return (
        <div className="studio-v2-preview-placeholder">
          Gallery block · {block.mediaIds.length} images · {block.columns} columns
        </div>
      );
  }
}

export function DocumentPreview({
  document,
  onClose,
}: DocumentPreviewProps) {
  const [mode, setMode] = useState<"visual" | "source">("visual");
  const sourceHtml = documentSourceHtml(document);

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

            {document.blocks.map(block => (
              <PreviewBlock key={block.id} block={block} />
            ))}

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
