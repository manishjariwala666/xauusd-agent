"use client";

import { useEffect, useState } from "react";

import {
  createEmptyDocument,
} from "@/lib/editor-v2/document-store";
import {
  cmsApiDetailToDocument,
  cmsDocumentToApiPayload,
  normalizeCmsDocument,
  type CmsApiContentDetail,
} from "@/lib/editor-v2/converters";
import type {
  CmsDocument,
} from "@/lib/editor-v2/document-types";
import {
  analyzeSeoDocument,
} from "@/lib/editor-v2/seo-analyzer";

import {
  ContentInsightsPanel,
} from "../seo/content-insights-panel";
import { DocumentCanvas } from "./document-canvas";
import { DocumentPreview } from "./document-preview";

const LOCAL_DRAFT_KEY = "venusrealm-custom-cms-v2-draft";

type SavedDraftItem = {
  id: number;
  title: string;
  slug: string;
  status: string;
  updated_at: string | null;
};

function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 160);
}

export function StudioWorkspace() {
  const [document, setDocument] = useState<CmsDocument | null>(null);
  const [slugEdited, setSlugEdited] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [saveMessage, setSaveMessage] = useState("Loading draft…");
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [savedDocumentSignature, setSavedDocumentSignature] =
    useState<string | null>(null);
  const [drafts, setDrafts] = useState<SavedDraftItem[]>([]);
  const [draftsLoading, setDraftsLoading] = useState(false);
  const [openingDraftId, setOpeningDraftId] =
    useState<number | null>(null);

  async function loadSavedDrafts() {
    setDraftsLoading(true);

    try {
      const response = await fetch(
        "/api/admin/content/posts?status=draft&page=1&page_size=50&sort=updated_desc",
        { cache: "no-store" },
      );

      const result = await response.json() as {
        items?: SavedDraftItem[];
        detail?: string;
        message?: string;
      };

      if (!response.ok) {
        throw new Error(
          result.detail ||
          result.message ||
          "Saved drafts could not be loaded.",
        );
      }

      setDrafts(Array.isArray(result.items) ? result.items : []);
    } catch (error) {
      setSaveMessage(
        error instanceof Error
          ? error.message
          : "Saved drafts could not be loaded.",
      );
    } finally {
      setDraftsLoading(false);
    }
  }

  async function openSavedDraft(draftId: number) {
    if (openingDraftId !== null) return;

    setOpeningDraftId(draftId);
    setSaveMessage(`Opening draft #${draftId}…`);

    try {
      const response = await fetch(
        `/api/admin/content/posts/${draftId}`,
        { cache: "no-store" },
      );

      const result = await response.json() as
        CmsApiContentDetail & {
          detail?: string;
          message?: string;
        };

      if (!response.ok || !result.id) {
        throw new Error(
          result.detail ||
          result.message ||
          "Draft could not be opened.",
        );
      }

      const loadedDocument = cmsApiDetailToDocument(result);

      window.localStorage.setItem(
        LOCAL_DRAFT_KEY,
        JSON.stringify(loadedDocument),
      );

      setSlugEdited(true);
      setDocument(loadedDocument);
      setSavedDocumentSignature(JSON.stringify(loadedDocument));
      setSaveMessage(`Draft #${draftId} opened`);
    } catch (error) {
      setSaveMessage(
        error instanceof Error
          ? error.message
          : "Draft could not be opened.",
      );
    } finally {
      setOpeningDraftId(null);
    }
  }

  useEffect(() => {
    void loadSavedDrafts();
  }, []);

  useEffect(() => {
    function handleSeoQuickAction(event: Event) {
      const customEvent = event as CustomEvent<{
        target?: string;
      }>;

      const target = customEvent.detail?.target;

      const selectors: Record<string, string> = {
        title: "[data-seo-target='title']",
        slug: "[data-seo-target='slug']",
        excerpt: "[data-seo-target='excerpt']",
        social: "[data-seo-target='social']",
        content: "[data-seo-target='content']",
        images: "[data-seo-target='content']",
      };

      const selector =
        target && selectors[target];

      if (!selector) return;

      const element =
        window.document.querySelector<HTMLElement>(
          selector,
        );

      if (!element) return;

      element.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });

      element.classList.add(
        "studio-seo-target-highlight",
      );

      window.setTimeout(() => {
        element.classList.remove(
          "studio-seo-target-highlight",
        );
      }, 1800);

      const input =
        element.matches("input, textarea, select")
          ? element
          : element.querySelector<
              HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
            >("input, textarea, select");

      input?.focus();
    }

    window.addEventListener(
      "studio-seo-quick-action",
      handleSeoQuickAction,
    );

    return () => {
      window.removeEventListener(
        "studio-seo-quick-action",
        handleSeoQuickAction,
      );
    };
  }, []);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(LOCAL_DRAFT_KEY);

      if (saved) {
        const restoredDocument = normalizeCmsDocument(
          JSON.parse(saved) as CmsDocument,
        );

        window.localStorage.setItem(
          LOCAL_DRAFT_KEY,
          JSON.stringify(restoredDocument),
        );

        setDocument(restoredDocument);
        setSaveMessage("Local draft restored and normalized");
        return;
      }
    } catch {
      setSaveMessage("Stored draft could not be restored");
    }

    setDocument(createEmptyDocument());
    setSaveMessage("New local draft");
  }, []);

  useEffect(() => {
    function handleStorage(event: StorageEvent) {
      if (
        event.key !== LOCAL_DRAFT_KEY ||
        !event.newValue
      ) {
        return;
      }

      try {
        const nextDocument = normalizeCmsDocument(
          JSON.parse(event.newValue) as CmsDocument,
        );

        setDocument(nextDocument);
      } catch {
        return;
      }
    }

    window.addEventListener("storage", handleStorage);

    return () => {
      window.removeEventListener("storage", handleStorage);
    };
  }, []);

  useEffect(() => {
    function handleDraftUpdate(event: Event) {
      const customEvent = event as CustomEvent<CmsDocument>;

      if (!customEvent.detail) return;

      setDocument(
        normalizeCmsDocument(customEvent.detail),
      );
    }

    window.addEventListener(
      "venusrealm:cms-draft-updated",
      handleDraftUpdate,
    );

    return () => {
      window.removeEventListener(
        "venusrealm:cms-draft-updated",
        handleDraftUpdate,
      );
    };
  }, []);

  useEffect(() => {
    if (!document) return;

    setSaveMessage("Unsaved changes");

    const timer = window.setTimeout(() => {
      const savedDocument: CmsDocument = {
        ...document,
        updatedAt: new Date().toISOString(),
      };

      window.localStorage.setItem(
        LOCAL_DRAFT_KEY,
        JSON.stringify(savedDocument),
      );

      setSaveMessage("Autosaved locally");
    }, 1200);

    return () => window.clearTimeout(timer);
  }, [document]);

  async function saveDraft() {
    if (!document || saving || publishing) return;

    if (document.status !== "draft") {
      setSaveMessage("Published content cannot be saved as a draft here.");
      return;
    }

    if (!document.title.trim()) {
      setSaveMessage("Article title is required");
      return;
    }

    const saveSeoAnalysis =
      analyzeSeoDocument(document);

    const seoWarningItems =
      saveSeoAnalysis.publishChecklist.items.filter(
        item =>
          item.required &&
          !item.passed &&
          [
            "meta-title",
            "meta-description",
            "focus-keyword",
            "canonical",
            "links",
            "image-alt",
          ].includes(item.id),
      );

    setSaving(true);
    setSaveMessage("Saving draft to database…");

    try {
      const csrfResponse = await fetch("/api/admin/auth/csrf", {
        cache: "no-store",
      });

      if (!csrfResponse.ok) {
        throw new Error("CSRF token could not be loaded.");
      }

      const csrfData = await csrfResponse.json() as {
        csrfToken: string;
      };

      const endpoint = document.id
        ? `/api/admin/content/posts/${document.id}`
        : "/api/admin/content/posts";

      const response = await fetch(endpoint, {
        method: document.id ? "PATCH" : "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfData.csrfToken,
        },
        body: JSON.stringify(
          cmsDocumentToApiPayload(document),
        ),
      });

      const result = await response.json() as {
        id?: number;
        updated_at?: string;
        detail?: string;
        message?: string;
      };

      if (!response.ok || !result.id) {
        throw new Error(
          result.detail ||
          result.message ||
          "Draft could not be saved.",
        );
      }

      const savedDocument: CmsDocument = {
        ...document,
        id: result.id,
        status: "draft",
        updatedAt:
          result.updated_at || new Date().toISOString(),
      };

      window.localStorage.setItem(
        LOCAL_DRAFT_KEY,
        JSON.stringify(savedDocument),
      );

      setDocument(savedDocument);
      setSavedDocumentSignature(JSON.stringify(savedDocument));

      window.dispatchEvent(
        new CustomEvent("venusrealm:seo-snapshot", {
          detail: savedDocument,
        }),
      );

      void loadSavedDrafts();

      const savedMessage = document.id
        ? `Draft #${result.id} updated`
        : `Draft #${result.id} saved to database`;

      setSaveMessage(
        seoWarningItems.length > 0
          ? `${savedMessage}. SEO warning: ${seoWarningItems.length} required item${seoWarningItems.length === 1 ? "" : "s"} need attention.`
          : `${savedMessage}. SEO checks passed.`,
      );
    } catch (error) {
      setSaveMessage(
        error instanceof Error
          ? error.message
          : "Content service is temporarily unavailable.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function publishDraft() {
    if (
      !document ||
      !document.id ||
      document.status !== "draft" ||
      saving ||
      publishing ||
      savedDocumentSignature !== JSON.stringify(document)
    ) return;

    const confirmed = window.confirm(
      `Publish draft #${document.id} now? It will become public immediately.`,
    );

    if (!confirmed) return;

    setPublishing(true);
    setSaveMessage(`Publishing draft #${document.id}…`);

    try {
      const csrfResponse = await fetch("/api/admin/auth/csrf", {
        cache: "no-store",
      });

      if (!csrfResponse.ok) {
        throw new Error("CSRF token could not be loaded.");
      }

      const csrfData = await csrfResponse.json() as {
        csrfToken: string;
      };

      const response = await fetch(
        `/api/admin/content/posts/${document.id}/publish`,
        {
          method: "POST",
          headers: {
            "X-CSRF-Token": csrfData.csrfToken,
          },
        },
      );

      const result = await response.json() as
        CmsApiContentDetail & {
          detail?: string;
          message?: string;
        };

      if (
        !response.ok ||
        !result.id ||
        result.status !== "published"
      ) {
        throw new Error(
          result.detail ||
          result.message ||
          "Draft could not be published.",
        );
      }

      const publishedDocument = cmsApiDetailToDocument(result);

      window.localStorage.setItem(
        LOCAL_DRAFT_KEY,
        JSON.stringify(publishedDocument),
      );

      setDocument(publishedDocument);
      setSavedDocumentSignature(JSON.stringify(publishedDocument));
      setSaveMessage(`Post #${result.id} published successfully`);

      window.dispatchEvent(
        new CustomEvent("venusrealm:seo-snapshot", {
          detail: publishedDocument,
        }),
      );

      void loadSavedDrafts();
    } catch (error) {
      setSaveMessage(
        error instanceof Error
          ? error.message
          : "Content service is temporarily unavailable.",
      );
    } finally {
      setPublishing(false);
    }
  }

  function createNewDraft() {
    const confirmed = window.confirm(
      "Start a new draft? The current local draft will be replaced.",
    );

    if (!confirmed) return;

    const nextDocument = createEmptyDocument();

    window.localStorage.setItem(
      LOCAL_DRAFT_KEY,
      JSON.stringify(nextDocument),
    );

    setSlugEdited(false);
    setDocument(nextDocument);
    setSavedDocumentSignature(null);
    setSaveMessage("New draft created");
  }

  if (!document) {
    return (
      <main className="studio-v2-page">
        <div className="studio-v2-loading">
          Loading Custom CMS workspace…
        </div>
      </main>
    );
  }

  const seoAnalysis = analyzeSeoDocument(document);
  const isSavedDatabaseDraft =
    document.id !== null &&
    document.status === "draft" &&
    savedDocumentSignature === JSON.stringify(document);

  const quickSeoChecks = [
    {
      id: "meta-title",
      label: "SEO title",
      passed:
        document.seo.metaTitle.trim().length >= 30 &&
        document.seo.metaTitle.trim().length <= 60,
    },
    {
      id: "meta-description",
      label: "Meta description",
      passed:
        document.seo.metaDescription.trim().length >= 120 &&
        document.seo.metaDescription.trim().length <= 160,
    },
    {
      id: "focus-keyword",
      label: "Focus keyword",
      passed:
        document.seo.focusKeyword.trim().length > 0,
    },
    {
      id: "internal-links",
      label: "Internal link",
      passed: seoAnalysis.links.internal > 0,
    },
    {
      id: "external-links",
      label: "External link",
      passed: seoAnalysis.links.external > 0,
    },
    {
      id: "image-alt",
      label: "Image ALT",
      passed:
        seoAnalysis.imageSeo.total === 0 ||
        seoAnalysis.imageSeo.missingAlt === 0,
    },
    {
      id: "readability",
      label: "Readability",
      passed: seoAnalysis.readability.score >= 50,
    },
  ];

  return (
    <main className="studio-v2-page">
      <header className="studio-v2-page-heading">
        <div>
          <span className="section-kicker">
            CUSTOM CONTENT ENGINE
          </span>

          <h1>Content Studio</h1>

          <p>
            Create structured articles with visual text,
            inline media, galleries and reusable blocks.
          </p>
        </div>

        <div className="studio-v2-heading-actions">
          <button
            type="button"
            className="text-button"
            onClick={createNewDraft}
          >
            New Draft
          </button>

          <button
            type="button"
            className="secondary-button"
            onClick={() => setPreviewOpen(true)}
          >
            Preview
          </button>

          <button
            type="button"
            className="primary-button"
            onClick={saveDraft}
            disabled={saving || publishing || document.status !== "draft"}
          >
            {saving ? "Saving…" : "Save Draft"}
          </button>

          <button
            type="button"
            className="primary-button"
            disabled
            title="Publishing is locked in this workspace."
          >
            {document.status === "published" ? "Published" : "Publish"}
          </button>
        </div>
      </header>

      <section className="studio-v2-document-fields">
        <div className="studio-v2-document-status">
          <div>
            <strong>Saved database drafts</strong>
            <span>
              {draftsLoading
                ? " Loading…"
                : ` ${drafts.length} available`}
            </span>
          </div>

          <button
            type="button"
            className="text-button"
            onClick={() => void loadSavedDrafts()}
            disabled={draftsLoading}
          >
            Refresh
          </button>
        </div>

        {drafts.length > 0 ? (
          <label className="studio-v2-draft-selector">
            <span>Open saved draft</span>

            <select
              value={document.id ?? ""}
              disabled={openingDraftId !== null}
              onChange={event => {
                const draftId = Number(event.target.value);

                if (draftId > 0) {
                  void openSavedDraft(draftId);
                }
              }}
            >
              <option value="">Select a database draft…</option>

              {drafts.map(draft => (
                <option key={draft.id} value={draft.id}>
                  #{draft.id} — {draft.title || "Untitled draft"}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <div className="studio-v2-document-status">
          <span>{saveMessage}</span>
          <strong>
            {document.status === "published" ? "Published" : "Draft"}
          </strong>
        </div>

        <label className="studio-v2-title-field" data-seo-target="title">
          <span>Article title</span>
          <input
            value={document.title}
            maxLength={240}
            placeholder="Add article title"
            onChange={event => {
              const title = event.target.value;

              setDocument(current =>
                current
                  ? {
                      ...current,
                      title,
                      slug: slugEdited
                        ? current.slug
                        : slugify(title),
                    }
                  : current,
              );
            }}
          />
        </label>

        <div className="studio-v2-meta-grid">
          <label data-seo-target="slug">
            <span>Slug</span>
            <input
              value={document.slug}
              maxLength={160}
              placeholder="article-url-slug"
              onChange={event => {
                setSlugEdited(true);

                setDocument(current =>
                  current
                    ? {
                        ...current,
                        slug: slugify(event.target.value),
                      }
                    : current,
                );
              }}
            />
          </label>

          <label>
            <span>Status</span>
            <select
              value={document.status === "published" ? "published" : "draft"}
              disabled
              aria-describedby="studio-v2-status-help"
            >
              <option value="draft">Draft</option>
              <option value="published">Published</option>
            </select>

            <small id="studio-v2-status-help">
              {document.status === "published"
                ? "This post is published and public."
                : "Publishing is currently locked. Draft creation, editing and preview remain available."}
              {" Scheduling is not enabled in this workspace."}
            </small>
          </label>
        </div>

        <label data-seo-target="excerpt">
          <span>Excerpt</span>
          <textarea
            value={document.excerpt}
            rows={3}
            maxLength={2000}
            placeholder="Write a short summary for cards and search results"
            onChange={event =>
              setDocument(current =>
                current
                  ? {
                      ...current,
                      excerpt: event.target.value,
                    }
                  : current,
              )
            }
          />
        </label>

        <section
          className="studio-v2-quick-seo-description"
          data-seo-target="seo"
        >
          <header>
            <div>
              <span className="section-kicker">
                QUICK SEO
              </span>
              <strong>Search optimization</strong>
            </div>

            <small>
              Autosaved with this draft
            </small>
          </header>

          <div className="studio-v2-quick-seo-grid">
            <label>
              <span>Focus keyword</span>
              <input
                value={document.seo.focusKeyword}
                maxLength={120}
                placeholder="Example: gold market analysis"
                onChange={event =>
                  setDocument(current =>
                    current
                      ? {
                          ...current,
                          seo: {
                            ...current.seo,
                            focusKeyword:
                              event.target.value,
                          },
                        }
                      : current,
                  )
                }
              />
            </label>

            <label>
              <span>
                SEO title
                <small
                  className={
                    document.seo.metaTitle.length > 60
                      ? "is-over-limit"
                      : document.seo.metaTitle.length >= 30
                        ? "is-recommended"
                        : ""
                  }
                >
                  {document.seo.metaTitle.length}
                  {" / "}60
                </small>
              </span>

              <input
                value={document.seo.metaTitle}
                maxLength={70}
                placeholder="Search result title"
                onChange={event =>
                  setDocument(current =>
                    current
                      ? {
                          ...current,
                          seo: {
                            ...current.seo,
                            metaTitle:
                              event.target.value,
                          },
                        }
                      : current,
                  )
                }
              />
            </label>
          </div>

          <label className="studio-v2-quick-seo-meta-description">
            <span>
              Meta description
              <small
                className={
                  document.seo.metaDescription.length > 160
                    ? "is-over-limit"
                    : document.seo.metaDescription.length >= 120
                      ? "is-recommended"
                      : ""
                }
              >
                {document.seo.metaDescription.length}
                {" / "}160
              </small>
            </span>

            <textarea
              value={document.seo.metaDescription}
              rows={4}
              maxLength={200}
              placeholder="Write a concise search result description"
              aria-describedby="studio-v2-meta-description-help"
              onChange={event =>
                setDocument(current =>
                  current
                    ? {
                        ...current,
                        seo: {
                          ...current.seo,
                          metaDescription:
                            event.target.value,
                        },
                      }
                    : current,
                )
              }
            />
          </label>

          <small id="studio-v2-meta-description-help">
            Recommended: SEO title 30–60 characters,
            meta description 120–160 characters.
          </small>

          <section
            className="studio-v2-quick-seo-preview"
            aria-label="Google search preview"
          >
            <span>GOOGLE SEARCH PREVIEW</span>

            <h3>
              {document.seo.metaTitle ||
                document.title ||
                "Untitled VenusRealm article"}
            </h3>

            <code>
              https://venusrealm.net/
              {document.slug || "article-slug"}
            </code>

            <p>
              {document.seo.metaDescription ||
                document.excerpt ||
                "Add a useful meta description for this article."}
            </p>
          </section>

          <section className="studio-v2-quick-seo-advanced-controls">
            <label>
              <span>Canonical URL</span>

              <input
                value={document.seo.canonicalUrl}
                placeholder={
                  document.slug
                    ? `https://venusrealm.net/${document.slug}`
                    : "https://venusrealm.net/article-slug"
                }
                onChange={event =>
                  setDocument(current =>
                    current
                      ? {
                          ...current,
                          seo: {
                            ...current.seo,
                            canonicalUrl:
                              event.target.value,
                          },
                        }
                      : current,
                  )
                }
              />
            </label>

            <div className="studio-v2-quick-seo-toggle-grid">
              <label>
                <input
                  type="checkbox"
                  checked={document.seo.robotsIndex}
                  onChange={event =>
                    setDocument(current =>
                      current
                        ? {
                            ...current,
                            seo: {
                              ...current.seo,
                              robotsIndex:
                                event.target.checked,
                            },
                          }
                        : current,
                    )
                  }
                />

                <span>Allow search indexing</span>
              </label>

              <label>
                <input
                  type="checkbox"
                  checked={document.seo.robotsFollow}
                  onChange={event =>
                    setDocument(current =>
                      current
                        ? {
                            ...current,
                            seo: {
                              ...current.seo,
                              robotsFollow:
                                event.target.checked,
                            },
                          }
                        : current,
                    )
                  }
                />

                <span>Allow link following</span>
              </label>
            </div>
          </section>

          <section className="studio-v2-live-seo-score">
            <header>
              <div>
                <span>LIVE SEO SCORE</span>
                <strong>
                  {seoAnalysis.seoScore}/100
                </strong>
              </div>

              <a
                className="secondary-button"
                href="/studio-v2/seo"
              >
                Open Advanced SEO
              </a>
            </header>

            <div className="studio-v2-live-seo-checks">
              {quickSeoChecks.map(check => (
                <article
                  key={check.id}
                  className={
                    check.passed
                      ? "is-passed"
                      : "is-missing"
                  }
                >
                  <span>
                    {check.passed ? "✓" : "!"}
                  </span>

                  <strong>{check.label}</strong>
                </article>
              ))}
            </div>

            <small>
              Links are counted only when they are
              clickable anchors, buttons or linked media.
            </small>
          </section>
        </section>
      </section>

      <section className="studio-v2-publishing-features">
        <header>
          <div>
            <span className="section-kicker">
              ARTICLE NAVIGATION
            </span>
            <h2>Automatic table of contents</h2>
          </div>
        </header>

        <article className="studio-v2-feature-card studio-v2-toc-settings">
          <label className="studio-v2-toggle-row">
            <div>
              <strong>Enable Auto TOC</strong>
              <small>
                Build navigation automatically from H2-H6 headings.
              </small>
            </div>

            <input
              type="checkbox"
              checked={document.toc.enabled}
              onChange={event =>
                setDocument(current =>
                  current
                    ? {
                        ...current,
                        toc: {
                          ...current.toc,
                          enabled: event.target.checked,
                        },
                      }
                    : current,
                )
              }
            />
          </label>

          <div className="studio-v2-toc-grid">
            <label>
              <span>TOC title</span>
              <input
                value={document.toc.title}
                maxLength={120}
                placeholder="Table of Contents"
                disabled={!document.toc.enabled}
                onChange={event =>
                  setDocument(current =>
                    current
                      ? {
                          ...current,
                          toc: {
                            ...current.toc,
                            title: event.target.value,
                          },
                        }
                      : current,
                  )
                }
              />
            </label>

            <label>
              <span>Maximum heading depth</span>
              <select
                value={document.toc.maxDepth}
                disabled={!document.toc.enabled}
                onChange={event =>
                  setDocument(current =>
                    current
                      ? {
                          ...current,
                          toc: {
                            ...current.toc,
                            maxDepth: Number(
                              event.target.value,
                            ) as 2 | 3 | 4 | 5 | 6,
                          },
                        }
                      : current,
                  )
                }
              >
                <option value={2}>H2 only</option>
                <option value={3}>H2-H3</option>
                <option value={4}>H2-H4</option>
                <option value={5}>H2-H5</option>
                <option value={6}>H2-H6</option>
              </select>
            </label>
          </div>
        </article>
      </section>

      <section className="studio-v2-publishing-features">
        <header>
          <div>
            <span className="section-kicker">
              ARTICLE ENGAGEMENT
            </span>
            <h2>Sharing and related posts</h2>
          </div>
        </header>

        <div className="studio-v2-feature-grid">
          <article
            className="studio-v2-feature-card"
            data-seo-target="social"
          >
            <label className="studio-v2-toggle-row">
              <div>
                <strong>Social sharing</strong>
                <small>
                  Show sharing buttons below the article.
                </small>
              </div>

              <input
                type="checkbox"
                checked={document.socialSharing.enabled}
                onChange={event =>
                  setDocument(current =>
                    current
                      ? {
                          ...current,
                          socialSharing: {
                            ...current.socialSharing,
                            enabled: event.target.checked,
                          },
                        }
                      : current,
                  )
                }
              />
            </label>

            <div className="studio-v2-platform-grid">
              {[
                ["whatsapp", "WhatsApp"],
                ["telegram", "Telegram"],
                ["facebook", "Facebook"],
                ["x", "X"],
                ["linkedin", "LinkedIn"],
                ["copy", "Copy Link"],
              ].map(([value, label]) => {
                const platform =
                  value as CmsDocument["socialSharing"]["platforms"][number];
                const checked =
                  document.socialSharing.platforms.includes(platform);

                return (
                  <label key={value}>
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={!document.socialSharing.enabled}
                      onChange={() =>
                        setDocument(current => {
                          if (!current) return current;

                          const platforms = checked
                            ? current.socialSharing.platforms.filter(
                                item => item !== platform,
                              )
                            : [
                                ...current.socialSharing.platforms,
                                platform,
                              ];

                          return {
                            ...current,
                            socialSharing: {
                              ...current.socialSharing,
                              platforms,
                            },
                          };
                        })
                      }
                    />
                    <span>{label}</span>
                  </label>
                );
              })}
            </div>
          </article>

          <article className="studio-v2-feature-card">
            <label className="studio-v2-toggle-row">
              <div>
                <strong>Related posts</strong>
                <small>
                  Add selected article cards below the content.
                </small>
              </div>

              <input
                type="checkbox"
                checked={document.relatedPosts.enabled}
                onChange={event =>
                  setDocument(current =>
                    current
                      ? {
                          ...current,
                          relatedPosts: {
                            ...current.relatedPosts,
                            enabled: event.target.checked,
                          },
                        }
                      : current,
                  )
                }
              />
            </label>

            <label>
              <span>Section heading</span>
              <input
                value={document.relatedPosts.heading}
                disabled={!document.relatedPosts.enabled}
                onChange={event =>
                  setDocument(current =>
                    current
                      ? {
                          ...current,
                          relatedPosts: {
                            ...current.relatedPosts,
                            heading: event.target.value,
                          },
                        }
                      : current,
                  )
                }
              />
            </label>

            <div className="studio-v2-related-editor">
              {document.relatedPosts.items.map((item, index) => (
                <div key={item.id} className="studio-v2-related-editor-row">
                  <input
                    value={item.title}
                    placeholder="Related post title"
                    disabled={!document.relatedPosts.enabled}
                    onChange={event =>
                      setDocument(current => {
                        if (!current) return current;

                        const items = [...current.relatedPosts.items];
                        items[index] = {
                          ...items[index],
                          title: event.target.value,
                        };

                        return {
                          ...current,
                          relatedPosts: {
                            ...current.relatedPosts,
                            items,
                          },
                        };
                      })
                    }
                  />

                  <input
                    value={item.url}
                    placeholder="/blog/related-article"
                    disabled={!document.relatedPosts.enabled}
                    onChange={event =>
                      setDocument(current => {
                        if (!current) return current;

                        const items = [...current.relatedPosts.items];
                        items[index] = {
                          ...items[index],
                          url: event.target.value,
                        };

                        return {
                          ...current,
                          relatedPosts: {
                            ...current.relatedPosts,
                            items,
                          },
                        };
                      })
                    }
                  />

                  <button
                    type="button"
                    className="text-button danger-link"
                    disabled={!document.relatedPosts.enabled}
                    onClick={() =>
                      setDocument(current =>
                        current
                          ? {
                              ...current,
                              relatedPosts: {
                                ...current.relatedPosts,
                                items:
                                  current.relatedPosts.items.filter(
                                    related => related.id !== item.id,
                                  ),
                              },
                            }
                          : current,
                      )
                    }
                  >
                    Remove
                  </button>
                </div>
              ))}

              <button
                type="button"
                className="secondary-button"
                disabled={
                  !document.relatedPosts.enabled ||
                  document.relatedPosts.items.length >= 6
                }
                onClick={() =>
                  setDocument(current =>
                    current
                      ? {
                          ...current,
                          relatedPosts: {
                            ...current.relatedPosts,
                            items: [
                              ...current.relatedPosts.items,
                              {
                                id: crypto.randomUUID(),
                                title: "",
                                url: "",
                                excerpt: "",
                              },
                            ],
                          },
                        }
                      : current,
                  )
                }
              >
                + Add related post
              </button>
            </div>
          </article>
        </div>
      </section>

      <div className="studio-editor-layout" data-seo-target="content">
        <DocumentCanvas
          initialDocument={document}
          onChange={canvasDocument =>
            setDocument(current =>
              current
                ? {
                    ...current,
                    blocks: canvasDocument.blocks,
                  }
                : canvasDocument,
            )
          }
        />

        <ContentInsightsPanel
          document={document}
          drafts={drafts}
          onFeaturedMediaChange={mediaId =>
            setDocument(current =>
              current
                ? {
                    ...current,
                    featuredMediaId: mediaId,
                  }
                : current,
            )
          }
        />
      </div>

      {previewOpen ? (
        <DocumentPreview
          document={document}
          onClose={() => setPreviewOpen(false)}
        />
      ) : null}
    </main>
  );
}
