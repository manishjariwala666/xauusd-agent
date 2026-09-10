"use client";

import { useEffect, useRef } from "react";

const LOCAL_DRAFT_KEY = "venusrealm-custom-cms-v2-draft";

type StoredDocument = {
  id?: number | null;
  status?: string;
  featuredMediaId?: number | null;
};

async function csrfToken(): Promise<string> {
  const response = await fetch("/api/admin/auth/csrf", {
    cache: "no-store",
    credentials: "same-origin",
  });

  if (!response.ok) throw new Error("CSRF token could not be loaded.");
  const payload = (await response.json()) as { csrfToken?: string };
  if (!payload.csrfToken) throw new Error("CSRF token is missing.");
  return payload.csrfToken;
}

export function PublishedFeaturedImageSync() {
  const lastSignature = useRef<string>("");
  const syncing = useRef(false);

  useEffect(() => {
    let cancelled = false;

    async function syncFromLocalStorage() {
      if (cancelled || syncing.current) return;

      const raw = window.localStorage.getItem(LOCAL_DRAFT_KEY);
      if (!raw) return;

      let document: StoredDocument;
      try {
        document = JSON.parse(raw) as StoredDocument;
      } catch {
        return;
      }

      const contentId = Number(document.id || 0);
      if (
        !Number.isInteger(contentId) ||
        contentId <= 0 ||
        document.status !== "published"
      ) {
        return;
      }

      const mediaId =
        document.featuredMediaId === null ||
        document.featuredMediaId === undefined
          ? null
          : Number(document.featuredMediaId);

      if (mediaId !== null && (!Number.isInteger(mediaId) || mediaId <= 0)) {
        return;
      }

      const signature = `${contentId}:${mediaId ?? "none"}`;
      if (signature === lastSignature.current) return;

      syncing.current = true;
      try {
        const token = await csrfToken();
        const response = await fetch(`/api/admin/featured-image/${contentId}`, {
          method: mediaId ? "POST" : "DELETE",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            "X-CSRF-Token": token,
            ...(mediaId ? { "Content-Type": "application/json" } : {}),
          },
          body: mediaId ? JSON.stringify({ media_id: mediaId }) : undefined,
        });

        if (response.ok) {
          lastSignature.current = signature;
        }
      } finally {
        syncing.current = false;
      }
    }

    void syncFromLocalStorage();
    const interval = window.setInterval(() => {
      void syncFromLocalStorage();
    }, 1500);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  return null;
}
