import "server-only";

import { getAdminServerConfig } from "./server-config";
import type { Paginated } from "./content-api";

export type SeoIssue = { code: string; severity: "warning" | "error"; message: string; points_lost: number };
export type SocialSeo = { title?: string; description?: string; image?: string; media_id?: number | null; image_alt?: string; card_type?: "summary" | "summary_large_image" };
export type FaqEntry = { question: string; answer: string };
export type SeoDetail = {
  content_id: number; slug: string; meta_title: string; meta_description: string;
  focus_keyword: string; secondary_keywords: string[]; canonical_url: string;
  robots_index: boolean; robots_follow: boolean; sitemap_included: boolean;
  open_graph: SocialSeo; twitter_card: SocialSeo; faq?: FaqEntry[];
  schema_jsonld?: Record<string, unknown> | unknown[]; seo_score: number;
  seo_validation_issues: SeoIssue[]; updated_at: string;
  content: { id: number; content_type: string; title: string; slug: string; excerpt: string; status: string; is_public: boolean; featured_image: string | null; featured_media_id: number | null; featured_image_alt: string | null; category: string | null; subcategory: string; published_at: string | null; updated_at: string };
};
export type SeoIssueItem = { id: number; content_type: string; title: string; slug: string; status: string; category: string | null; updated_at: string; seo_score: number; issues: SeoIssue[] };
export type SeoSummary = { total: number; average_score: number; low_score: number; missing_title: number; missing_description: number; noindex: number };

async function seoFetch<T>(path: string, token: string): Promise<T | null> {
  if (!token) return null;
  try {
    const config = getAdminServerConfig();
    const response = await fetch(`${config.backendBaseUrl}/admin/${path}`, { headers: { Authorization: `Bearer ${token}`, "X-Admin-BFF-Key": config.bffSecret }, cache: "no-store", signal: AbortSignal.timeout(5000) });
    return response.ok ? await response.json() as T : null;
  } catch { return null; }
}

export const fetchSeoDetail = (id: string, token: string) => seoFetch<SeoDetail>(`content/${encodeURIComponent(id)}/seo`, token);
export const fetchSeoIssues = (query: URLSearchParams, token: string) => seoFetch<Paginated<SeoIssueItem>>(`seo/issues?${query}`, token);
export const fetchSeoSummary = (token: string) => seoFetch<SeoSummary>("seo/summary", token);
