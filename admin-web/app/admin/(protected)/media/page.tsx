import { cookies } from "next/headers";
import { MediaLibrary } from "@/components/media-library";
import { fetchMediaList } from "@/lib/media-api";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

export default async function MediaPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams;
  const query = new URLSearchParams({
    page: String(params.page || "1"), page_size: "24", search: String(params.search || ""),
    source: String(params.source || "all"), state: String(params.state || "active"),
    date_filter: String(params.date_filter || "all")
  });
  const token = (await cookies()).get(ADMIN_SESSION_COOKIE)?.value || "";
  const data = await fetchMediaList(query, token);
  if (!data) return <section className="state-panel error-state"><strong>Media could not be loaded.</strong><p>Check the isolated media service and try again.</p></section>;
  return <MediaLibrary data={data} filters={Object.fromEntries(query)} selectFor={params.selectFor ? Number(params.selectFor) : undefined} />;
}
