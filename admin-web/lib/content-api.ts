import "server-only";

import { getAdminServerConfig } from "./server-config";

export type ContentSummary = {
  id: number; title: string; slug: string; content_type: string;
  status: "draft" | "published" | "scheduled" | "trash"; category: string | null;
  author: string | null; published_at: string | null;
  scheduled_at: string | null; updated_at: string;
  views: number; seo_score: number; featured_image: string | null;
};
export type ContentDetail = ContentSummary & {
  excerpt: string; body: string; category_id: number | null;
  subcategory: string; is_public: boolean; created_at: string;
  meta_title: string | null; meta_description: string | null;
  focus_keyword: string | null; faq: Array<Record<string, unknown>>;
  schema_jsonld: Record<string, unknown>; open_graph: Record<string, unknown>;
  twitter_card: Record<string, unknown>;
};
export type Category = {
  id: number; title: string; slug: string; description: string;
  display_order: number; is_public: boolean; is_active: boolean; updated_at: string;
};
export type ContentStats = { total: number; published: number; drafts: number; scheduled: number; trashed: number; total_views: number };
export type Paginated<T> = { items: T[]; page: number; page_size: number; total: number; pages: number; stats?: ContentStats };

async function adminFetch<T>(path: string, token: string): Promise<T | null> {
  if (!token) return null;
  try {
    const config = getAdminServerConfig();
    const response = await fetch(`${config.backendBaseUrl}/admin/content/${path}`, {
      headers: { Authorization: `Bearer ${token}`, "X-Admin-BFF-Key": config.bffSecret },
      cache: "no-store",
      signal: AbortSignal.timeout(4000)
    });
    if (!response.ok) return null;
    return await response.json() as T;
  } catch { return null; }
}

export function fetchContentList(kind: "posts" | "pages", query: URLSearchParams, token: string) {
  return adminFetch<Paginated<ContentSummary>>(`${kind}?${query.toString()}`, token);
}
export function fetchContentDetail(kind: "posts" | "pages", id: string, token: string) {
  return adminFetch<ContentDetail>(`${kind}/${encodeURIComponent(id)}`, token);
}
export function fetchCategories(query: URLSearchParams, token: string) {
  return adminFetch<Paginated<Category>>(`categories?${query.toString()}`, token);
}
