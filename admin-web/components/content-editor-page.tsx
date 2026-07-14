import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { ContentEditor } from "./content-editor";
import { fetchCategories, fetchContentDetail } from "@/lib/content-api";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

export async function ContentEditorPage({ kind, id }: {
  kind: "posts" | "pages"; id?: string;
}) {
  const token = (await cookies()).get(ADMIN_SESSION_COOKIE)?.value || "";
  const categories = await fetchCategories(new URLSearchParams({ page_size: "50", active: "active" }), token);
  const initial = id ? await fetchContentDetail(kind, id, token) : null;
  if (id && !initial) notFound();
  const publicWebsiteUrl = (process.env.PUBLIC_WEBSITE_URL || "").trim().replace(/\/$/, "");
  return <ContentEditor kind={kind} initial={initial} categories={categories?.items || []} publicWebsiteUrl={publicWebsiteUrl || undefined} />;
}
