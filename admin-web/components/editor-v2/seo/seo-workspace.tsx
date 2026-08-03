"use client";

import { useEffect, useState } from "react";

import {
  analyzeSeoDocument,
} from "@/lib/editor-v2/seo-analyzer";
import type {
  CmsDocument,
} from "@/lib/editor-v2/document-types";

const DRAFT_KEY = "venusrealm-custom-cms-v2-draft";

export function SeoWorkspace() {
  const [document, setDocument] =
    useState<CmsDocument | null>(null);

  const [message, setMessage] = useState("");

  useEffect(() => {
    try {
      const saved =
        window.localStorage.getItem(DRAFT_KEY);

      if (saved) {
        setDocument(
          JSON.parse(saved) as CmsDocument,
        );

        return;
      }
    } catch {
      setMessage(
        "Local content draft could not be read.",
      );
    }

    setMessage(
      "Content Studio me draft create aur save karein.",
    );
  }, []);

  if (!document) {
    return (
      <div className="studio-v2-module-placeholder">
        {message || "Loading SEO data…"}
      </div>
    );
  }

  const analysis = analyzeSeoDocument(document);
  const score = analysis.seoScore;

  function updateSeo<
    Key extends keyof CmsDocument["seo"],
  >(
    key: Key,
    value: CmsDocument["seo"][Key],
  ) {
    setDocument(current =>
      current
        ? {
            ...current,
            seo: {
              ...current.seo,
              [key]: value,
            },
          }
        : current,
    );
  }

  function saveSeoSettings() {
    if (!document) return;

    const savedDocument: CmsDocument = {
      ...document,
      updatedAt: new Date().toISOString(),
    };

    window.localStorage.setItem(
      DRAFT_KEY,
      JSON.stringify(savedDocument),
    );

    window.dispatchEvent(
      new CustomEvent("venusrealm:cms-draft-updated", {
        detail: savedDocument,
      }),
    );

    setDocument(savedDocument);

    setMessage(
      "SEO settings current draft me save ho gayi.",
    );
  }

  function generateBasicSchema() {
    if (!document) return;

    const schema = {
      "@context": "https://schema.org",
      "@type": "Article",
      headline:
        document.seo.metaTitle ||
        document.title ||
        "Untitled article",
      description:
        document.seo.metaDescription ||
        document.excerpt ||
        "",
      url:
        document.seo.canonicalUrl ||
        `https://venusrealm.net/${document.slug}`,
    };

    updateSeo("schemaJsonLd", schema);

    setMessage(
      "Basic Article schema generated. Save SEO settings karein.",
    );
  }

  return (
    <section className="studio-seo-workspace">
      <aside className="studio-seo-score-card">
        <div className="studio-seo-score-ring">
          <strong>{score}</strong>
          <span>/ 100</span>
        </div>

        <h2>SEO readiness</h2>

        <p>
          Deterministic checks hain; ranking guarantee
          nahi hai.
        </p>
      </aside>

      <div className="studio-seo-form">
        <label>
          <span>Focus keyword</span>

          <input
            value={document.seo.focusKeyword}
            maxLength={120}
            placeholder="Example: gold market analysis"
            onChange={event =>
              updateSeo(
                "focusKeyword",
                event.target.value,
              )
            }
          />
        </label>

        <label>
          <span>Meta title</span>

          <input
            value={document.seo.metaTitle}
            maxLength={70}
            placeholder="Search result title"
            onChange={event =>
              updateSeo(
                "metaTitle",
                event.target.value,
              )
            }
          />

          <small>
            {document.seo.metaTitle.length}
            {" / "}60 recommended characters
          </small>
        </label>

        <label>
          <span>Meta description</span>

          <textarea
            value={document.seo.metaDescription}
            rows={5}
            maxLength={200}
            placeholder="Concise search result description"
            onChange={event =>
              updateSeo(
                "metaDescription",
                event.target.value,
              )
            }
          />

          <small>
            {document.seo.metaDescription.length}
            {" / "}160 recommended characters
          </small>
        </label>

        <label>
          <span>Canonical URL</span>

          <input
            value={document.seo.canonicalUrl}
            placeholder="https://venusrealm.net/article-slug"
            onChange={event =>
              updateSeo(
                "canonicalUrl",
                event.target.value,
              )
            }
          />
        </label>

        <div className="studio-seo-checks">
          <label>
            <input
              type="checkbox"
              checked={document.seo.robotsIndex}
              onChange={event =>
                updateSeo(
                  "robotsIndex",
                  event.target.checked,
                )
              }
            />

            Allow search indexing
          </label>

          <label>
            <input
              type="checkbox"
              checked={document.seo.robotsFollow}
              onChange={event =>
                updateSeo(
                  "robotsFollow",
                  event.target.checked,
                )
              }
            />

            Allow link following
          </label>
        </div>

        <div className="studio-seo-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={generateBasicSchema}
          >
            Generate Article Schema
          </button>

          <button
            type="button"
            className="primary-button"
            onClick={saveSeoSettings}
          >
            Save SEO Settings
          </button>
        </div>

        {message ? (
          <div
            className="studio-media-message"
            role="status"
          >
            {message}
          </div>
        ) : null}

        <details className="studio-seo-schema">
          <summary>JSON-LD schema preview</summary>

          <pre>
            {JSON.stringify(
              document.seo.schemaJsonLd,
              null,
              2,
            )}
          </pre>
        </details>
      </div>

      <aside className="studio-seo-preview">
        <span>SEARCH PREVIEW</span>

        <h2>
          {document.seo.metaTitle ||
            document.title ||
            "Untitled VenusRealm article"}
        </h2>

        <code>
          venusrealm.net/
          {document.slug || "article-slug"}
        </code>

        <p>
          {document.seo.metaDescription ||
            document.excerpt ||
            "Add a useful meta description for this article."}
        </p>

        <hr />

        <strong>Current checks</strong>

        <ul>
          <li>
            Article title:
            {" "}
            {document.title
              ? "Available"
              : "Missing"}
          </li>

          <li>
            Slug:
            {" "}
            {document.slug
              ? "Available"
              : "Missing"}
          </li>

          <li>
            Focus keyword:
            {" "}
            {document.seo.focusKeyword
              ? "Available"
              : "Missing"}
          </li>

          <li>
            Meta title:
            {" "}
            {document.seo.metaTitle
              ? "Available"
              : "Missing"}
          </li>

          <li>
            Meta description:
            {" "}
            {document.seo.metaDescription
              ? "Available"
              : "Missing"}
          </li>

          <li>
            Indexing:
            {" "}
            {document.seo.robotsIndex
              ? "Allowed"
              : "Blocked"}
          </li>
        </ul>
      </aside>
    </section>
  );
}
