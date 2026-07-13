import { cookies } from "next/headers";
import { ContentList } from "./content-list";
import { fetchContentList } from "@/lib/content-api";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

export async function ContentIndexPage({ kind, searchParams }: {
  kind: "posts" | "pages";
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const query = new URLSearchParams({
    page: String(params.page || "1"), page_size: "20",
    search: String(params.search || ""), status: String(params.status || "all")
  });
  const token = (await cookies()).get(ADMIN_SESSION_COOKIE)?.value || "";
  const data = await fetchContentList(kind, query, token);
  if (!data) return <section className="state-panel error-state"><strong>Content could not be loaded.</strong><p>Try again after checking the local staging API.</p></section>;
  const publicWebsiteUrl = (process.env.PUBLIC_WEBSITE_URL || "").trim().replace(/\/$/, "");
  return <ContentList kind={kind} data={data} search={query.get("search") || ""} status={query.get("status") || "all"} publicWebsiteUrl={publicWebsiteUrl || undefined} />;
}
