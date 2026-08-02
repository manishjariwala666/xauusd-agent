"use client";

import type {
  CmsBlock,
  CmsDocument,
} from "@/lib/editor-v2/document-types";

type DocumentPreviewProps = {
  document: CmsDocument;
  onClose: () => void;
};

function PreviewBlock({ block }: { block: CmsBlock }) {
  switch (block.type) {
    case "paragraph":
      return (
        <div
          className="studio-v2-preview-richtext"
          dangerouslySetInnerHTML={{ __html: block.html }}
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
          dangerouslySetInnerHTML={{ __html: block.html }}
        />
      );

    case "quote":
      return (
        <blockquote>
          <div dangerouslySetInnerHTML={{ __html: block.html }} />
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

          <button
            type="button"
            className="secondary-button"
            onClick={onClose}
          >
            Close preview
          </button>
        </header>

        <article className="studio-v2-preview-article">
          {document.excerpt ? (
            <p className="studio-v2-preview-excerpt">
              {document.excerpt}
            </p>
          ) : null}

          {document.blocks.map(block => (
            <PreviewBlock key={block.id} block={block} />
          ))}
        </article>
      </section>
    </div>
  );
}
