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

export type ContentQualityCheck = {
  code: string;
  passed: boolean;
  severity: "warning" | "error";
  message: string;
};

export type DuplicateMatch = {
  id: number;
  title: string;
  slug: string;
  status: "draft" | "published";
  title_similarity: number;
  body_similarity: number;
  similarity: number;
  exact_slug_match: boolean;
};

export type ContentAnalysis = {
  content_id: number;
  quality: {
    score: number;
    word_count: number;
    character_count: number;
    reading_time_minutes: number;
    headings: Record<"h2" | "h3" | "h4" | "h5" | "h6", number>;
    focus_keyword_count: number;
    focus_keyword_density: number;
    internal_links: number;
    external_links: number;
    images: number;
    images_missing_alt: number;
    repeated_sentences: Array<{ text: string; count: number }>;
    checks: ContentQualityCheck[];
  };
  duplicates: {
    risk: "low" | "medium" | "high";
    highest_similarity: number;
    matches: DuplicateMatch[];
    scope: "internal_database_only";
  };
  originality_score: number;
  overall_score: number;
};

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
