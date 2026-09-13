"use client";

import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

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
  const [publishedJustNow, setPublishedJustNow] = useState(false);
  const [actionHost, setActionHost] = useState<HTMLElement | null>(null);

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

  useEffect(() => {
    if (!isPublished) {
      setActionHost(null);
      return;
    }

    const host = window.document.querySelector<HTMLElement>(
      ".studio-v2-page-heading .studio-v2-heading-actions",
    );

    if (!host) return;

    const originalButtons = Array.from(
      host.querySelectorAll<HTMLButtonElement>("button"),
    ).filter(button => {
      if (button.dataset.publishedAction === "true") return false;
      const label = button.textContent?.trim() || "";
      return label === "Save Draft" || label === "Published";
    });

    const previousDisplays = originalButtons.map(button => button.style.display);
    originalButtons.forEach(button => {
      button.style.display = "none";
    });
    setActionHost(host);

    return () => {
      originalButtons.forEach((button, index) => {
        button.style.display = previousDisplays[index] || "";
      });
    };
  }, [isPublished]);

  useEffect(() => {
    if (dirty) setPublishedJustNow(false);
  }, [dirty]);

  if (!document || !isPublished || !actionHost) return null;

  const publicUrl = document.slug.trim()
    ? `https://venusrealm.net/blog/${encodeURIComponent(document.slug.trim())}`
    : "";

  async function updatePublishedPost() {
    const current = document;
    if (!current?.id || !dirty || updating) return;

    if (!current.title.trim()) {
      window.alert("Article title is required.");
      return;
    }

    setUpdating(true);

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
        `/api/admin/content/posts/${current.id}`,
        {
          method: "PATCH",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrfData.csrfToken,
          },
          body: JSON.stringify({
            title: current.title.trim(),
            slug: current.slug.trim(),
            excerpt: current.excerpt.trim(),
            body: cmsDocumentToHtml(current),
            category_id: current.categoryId,
            subcategory: "",
            status: "published",
            scheduled_at: null,
            published_at: current.publishedAt,
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
      setPublishedJustNow(true);
    } catch (error) {
      window.alert(
        error instanceof Error
          ? error.message
          : "Published post could not be updated.",
      );
    } finally {
      setUpdating(false);
    }
  }

  return createPortal(
    <>
      {publicUrl ? (
        <a
          className="secondary-button"
          href={publicUrl}
          target="_blank"
          rel="noopener noreferrer"
          data-published-action="true"
        >
          View Post ↗
        </a>
      ) : null}

      <button
        type="button"
        className="primary-button"
        data-published-action="true"
        onClick={() => void updatePublishedPost()}
        disabled={!dirty || updating}
        title={
          dirty
            ? "Publish the latest edits to the live post."
            : "The live post is up to date."
        }
      >
        {updating
          ? "Publishing…"
          : dirty
            ? "Update & Publish"
            : publishedJustNow
              ? "Published ✓"
              : "Published"}
      </button>
    </>,
    actionHost,
  );
}
