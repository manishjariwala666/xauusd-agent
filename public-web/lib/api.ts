import { cache } from "react";
import type { Category, ContentItem, Signal } from "./types";

const API_BASE = (
  process.env.BACKEND_BASE_URL ||
  "https://xauusd-agent-api-production.up.railway.app"
).replace(/\/$/, "");

async function fetchJson<T>(
  path: string,
  fallback: T,
  revalidate = 60
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 2000);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      signal: controller.signal,
      next: { revalidate }
    });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  } finally {
    clearTimeout(timeout);
  }
}

export async function getCategories(): Promise<Category[]> {
  const response = await fetchJson<{ items: Category[] }>(
    "/public/categories",
    { items: [] },
    300
  );
  return response.items;
}

export async function getContent(
  contentType?: string,
  limit = 12
): Promise<ContentItem[]> {
  const query = new URLSearchParams({ limit: String(limit) });
  if (contentType) query.set("content_type", contentType);
  const response = await fetchJson<{ items: ContentItem[] }>(
    `/public/content?${query}`,
    { items: [] },
    300
  );
  return response.items;
}

async function fetchContentDetail(slug: string): Promise<ContentItem | null> {
  const response = await fetchJson<{ item: ContentItem | null }>(
    `/public/content/${encodeURIComponent(slug)}`,
    { item: null },
    300
  );
  return response.item;
}

// Metadata and page rendering request the same article. React cache guarantees
// that the API receives one detail request per render instead of two.
export const getContentDetail = cache(fetchContentDetail);

export async function getSignals(): Promise<Signal[]> {
  const response = await fetchJson<{ items: Signal[] }>(
    "/public/signals?limit=12",
    { items: [] },
    0
  );
  return response.items;
}

export async function getSignalSnapshot(): Promise<Signal[]> {
  const response = await fetchJson<{ items: Signal[] }>(
    "/public/signals?limit=3",
    { items: [] },
    300
  );
  return response.items;
}

export function siteUrl(path = ""): string {
  const base = (process.env.NEXT_PUBLIC_SITE_URL || "https://venusrealm.net").replace(/\/$/, "");
  return `${base}/${path.replace(/^\//, "")}`;
}
