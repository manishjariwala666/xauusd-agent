import { cookies } from "next/headers";
import { SeoDashboard } from "@/components/seo-dashboard";
import { fetchCategories } from "@/lib/content-api";
import { fetchSeoIssues, fetchSeoSummary } from "@/lib/seo-api";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

export default async function SeoPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams; const token = (await cookies()).get(ADMIN_SESSION_COOKIE)?.value || "";
  const query = new URLSearchParams({ page: String(params.page || "1"), page_size: "20", content_type: String(params.content_type || "all"), status: String(params.status || "all"), min_score: String(params.min_score || "0"), max_score: String(params.max_score || "100"), issue_type: String(params.issue_type || "all") });
  if (params.category_id) query.set("category_id", String(params.category_id));
  const [data, summary, categories] = await Promise.all([fetchSeoIssues(query, token), fetchSeoSummary(token), fetchCategories(new URLSearchParams({ page_size: "50", active: "active" }), token)]);
  if (!data || !summary) return <section className="state-panel error-state"><strong>SEO data could not be loaded.</strong><p>Check the isolated SEO service and try again.</p></section>;
  return <SeoDashboard data={data} summary={summary} categories={categories?.items || []} filters={Object.fromEntries(query)} publicWebsiteUrl={(process.env.PUBLIC_WEBSITE_URL || "").replace(/\/$/, "") || undefined} />;
}
