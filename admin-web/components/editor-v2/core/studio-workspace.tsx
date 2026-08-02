"use client";

import { useEffect, useState } from "react";

import {
  createEmptyDocument,
} from "@/lib/editor-v2/document-store";
import {
  cmsApiDetailToDocument,
  cmsDocumentToApiPayload,
  type CmsApiContentDetail,
} from "@/lib/editor-v2/converters";
import type {
  CmsDocument,
} from "@/lib/editor-v2/document-types";

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
    try {
      const saved = window.localStorage.getItem(LOCAL_DRAFT_KEY);

      if (saved) {
        setDocument(JSON.parse(saved) as CmsDocument);
        setSaveMessage("Local draft restored");
        return;
      }
    } catch {
      setSaveMessage("Stored draft could not be restored");
    }

    setDocument(createEmptyDocument());
    setSaveMessage("New local draft");
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
    if (!document || saving) return;

    if (!document.title.trim()) {
      setSaveMessage("Article title is required");
      return;
    }

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
      void loadSavedDrafts();
      setSaveMessage(
        document.id
          ? `Draft #${result.id} updated`
          : `Draft #${result.id} saved to database`,
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
            disabled={saving}
          >
            {saving ? "Saving…" : "Save Draft"}
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
          <div className="studio-v2-draft-list">
            {drafts.map(draft => (
              <button
                type="button"
                key={draft.id}
                className="studio-v2-draft-item"
                onClick={() => void openSavedDraft(draft.id)}
                disabled={openingDraftId !== null}
              >
                <strong>
                  {draft.title || `Untitled draft #${draft.id}`}
                </strong>
                <span>
                  #{draft.id} · {draft.slug || "no-slug"}
                </span>
                <small>
                  {openingDraftId === draft.id
                    ? "Opening…"
                    : draft.updated_at
                      ? new Date(
                          draft.updated_at,
                        ).toLocaleString()
                      : "No update date"}
                </small>
              </button>
            ))}
          </div>
        ) : null}
        <div className="studio-v2-document-status">
          <span>{saveMessage}</span>
          <strong>{document.status}</strong>
        </div>

        <label className="studio-v2-title-field">
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
          <label>
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
              value={document.status}
              onChange={event =>
                setDocument(current =>
                  current
                    ? {
                        ...current,
                        status:
                          event.target.value as CmsDocument["status"],
                      }
                    : current,
                )
              }
            >
              <option value="draft">Draft</option>
              <option value="scheduled">Scheduled</option>
              <option value="published">Published</option>
              <option value="trash">Trash</option>
            </select>
          </label>
        </div>

        <label>
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
      </section>

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

      {previewOpen ? (
        <DocumentPreview
          document={document}
          onClose={() => setPreviewOpen(false)}
        />
      ) : null}
    </main>
  );
}
