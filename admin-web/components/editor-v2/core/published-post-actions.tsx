"use client";

import { useEffect, useMemo, useState } from "react";

import {
  cmsApiDetailToDocument,
  cmsDocumentToHtml,
  normalizeCmsDocument,
  type CmsApiContentDetail,
} from "@/lib/editor-v2/converters";
import type { CmsDocument } from "@/lib/editor-v2/document-types";

const LOCAL_DRAFT_KEY = "venusrealm-custom-cms-v2-draft";

function editableSignature(document: CmsDocument): string {
  return JSON.stringify({
    id: document.id,
    title: document.title,
    slug: document.slug,
    excerpt: document.excerpt,
    categoryId: document.categoryId,
    featuredMediaId: document.featuredMediaId,
    blocks: document.blocks,
    seo: document.seo,
    socialSharing: document.socialSharing,
    relatedPosts: document.relatedPosts,
    toc: document.toc,
  });
}

function readStoredDocument(): CmsDocument | null {
  const raw = window.localStorage.getItem(LOCAL_DRAFT_KEY);
  if (!raw) return null;

  try {
    return normalizeCmsDocument(JSON.parse(raw) as CmsDocument);
  } catch {
    return null;
  }
}

export function PublishedPostActions() {
  const [document, setDocument] = useState<CmsDocument | null>(null);
  const [baseline, setBaseline] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let cancelled = false;

    function syncFromStorage() {
      if (cancelled) return;
      const next = readStoredDocument();
      if (!next) return;

      setDocument(next);
      if (next.status === "published") {
        setBaseline(current => current ?? editableSignature(next));
      } else {
        setBaseline(null);
      }
    }

    syncFromStorage();
    const interval = window.setInterval(syncFromStorage, 800);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  const isPublished =
    document?.status === "published" && Boolean(document.id);

  const dirty = useMemo(() => {
    if (!document || !isPublished || baseline === null) return false;
    return editableSignature(document) !== baseline;
  }, [document, isPublished, baseline]);

  if (!document || !isPublished) return null;

  const publicUrl = document.slug.trim()
    ? `https://venusrealm.net/blog/${encodeURIComponent(document.slug.trim())}`
    : "";

  async function updatePublishedPost() {
    if (!document.id || !dirty || updating) return;

    if (!document.title.trim()) {
      setMessage("Article title is required.");
      return;
    }

    setUpdating(true);
    setMessage(`Updating published post #${document.id}…`);

    try {
      const csrfResponse = await fetch("/api/admin/auth/csrf", {
        cache: "no-store",
        credentials: "same-origin",
      });

      if (!csrfResponse.ok) {
        throw new Error("CSRF token could not be loaded.");
      }

      const csrfData = await csrfResponse.json() as {
        csrfToken?: string;
      };

      if (!csrfData.csrfToken) {
        throw new Error("CSRF token is missing.");
      }

      const response = await fetch(
        `/api/admin/content/posts/${document.id}`,
        {
          method: "PATCH",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrfData.csrfToken,
          },
          body: JSON.stringify({
            title: document.title.trim(),
            slug: document.slug.trim(),
            excerpt: document.excerpt.trim(),
            body: cmsDocumentToHtml(document),
            category_id: document.categoryId,
            subcategory: "",
            status: "published",
            scheduled_at: null,
            published_at: document.publishedAt,
          }),
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
          "Published post could not be updated.",
        );
      }

      const saved = cmsApiDetailToDocument(result);

      window.localStorage.setItem(
        LOCAL_DRAFT_KEY,
        JSON.stringify(saved),
      );

      window.dispatchEvent(
        new CustomEvent("venusrealm:cms-draft-updated", {
          detail: saved,
        }),
      );

      setDocument(saved);
      setBaseline(editableSignature(saved));
      setMessage(`Post #${saved.id} updated and remains published.`);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Published post could not be updated.",
      );
    } finally {
      setUpdating(false);
    }
  }

  return (
    <section
      className="studio-v2-document-status"
      aria-label="Published post actions"
      style={{ margin: "20px auto 0", maxWidth: 1240 }}
    >
      <div>
        <strong>Published post</strong>
        <span>
          {message
            ? ` ${message}`
            : dirty
              ? " Unsaved live changes"
              : " Live version is up to date"}
        </span>
      </div>

      <div className="studio-v2-heading-actions">
        {publicUrl ? (
          <a
            className="secondary-button"
            href={publicUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            View Post ↗
          </a>
        ) : null}

        <button
          type="button"
          className="primary-button"
          onClick={() => void updatePublishedPost()}
          disabled={!dirty || updating}
          title={
            dirty
              ? "Save changes to the live published post."
              : "No unpublished changes."
          }
        >
          {updating
            ? "Updating…"
            : dirty
              ? "Update Published Post"
              : "Published"}
        </button>
      </div>
    </section>
  );
}
