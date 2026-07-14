import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { ContentEditor } from "./content-editor";
import { fetchCategories, fetchContentDetail } from "@/lib/content-api";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";
import { fetchSeoDetail } from "@/lib/seo-api";

export async function ContentEditorPage({ kind, id }: {
  kind: "posts" | "pages"; id?: string;
}) {
  const token = (await cookies()).get(ADMIN_SESSION_COOKIE)?.value || "";
  const [categories, initial, seo] = await Promise.all([
    fetchCategories(new URLSearchParams({ page_size: "50", active: "active" }), token),
    id ? fetchContentDetail(kind, id, token) : Promise.resolve(null),
    id ? fetchSeoDetail(id, token) : Promise.resolve(null)
  ]);
  if (id && !initial) notFound();
  const publicWebsiteUrl = (process.env.PUBLIC_WEBSITE_URL || "").trim().replace(/\/$/, "");
  return <ContentEditor kind={kind} initial={initial} seo={seo} categories={categories?.items || []} publicWebsiteUrl={publicWebsiteUrl || undefined} />;
}
