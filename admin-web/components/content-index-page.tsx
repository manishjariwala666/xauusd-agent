import Link from "next/link";
import { cookies } from "next/headers";
import { ContentList } from "./content-list";
import { fetchContentList } from "@/lib/content-api";
import { fetchCategories } from "@/lib/content-api";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

export async function ContentIndexPage({ kind, searchParams }: {
  kind: "posts" | "pages";
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const query = new URLSearchParams({
    page: String(params.page || "1"), page_size: "20",
    search: String(params.search || ""), status: String(params.status || "all"),
    sort: String(params.sort || "updated_desc")
  });
  if (params.category) query.set("category_id", String(params.category));
  const token = (await cookies()).get(ADMIN_SESSION_COOKIE)?.value || "";
  const [data, categories] = await Promise.all([
    fetchContentList(kind, query, token),
    fetchCategories(new URLSearchParams({ page_size: "50", active: "active" }), token)
  ]);
  if (!data) {
    if (kind === "posts") {
      return (
        <section>
          <header className="studio-header">
            <div>
              <span className="section-kicker">Publishing desk</span>
              <h1>Blog Studio</h1>
              <p>Create and manage website blog posts.</p>
            </div>
            <Link className="primary-button" href="/admin/posts/new">
              Create New Post
            </Link>
          </header>

          <section className="state-panel error-state">
            <strong>Existing posts could not be loaded.</strong>
            <p>You can still create a new blog post using the button above.</p>
          </section>
        </section>
      );
    }

    return (
      <section className="state-panel error-state">
        <strong>Content could not be loaded.</strong>
        <p>Try again after checking the local staging API.</p>
      </section>
    );
  }
  const publicWebsiteUrl = (process.env.PUBLIC_WEBSITE_URL || "").trim().replace(/\/$/, "");
  return <ContentList kind={kind} data={data} categories={categories?.items || []}
    search={query.get("search") || ""} status={query.get("status") || "all"}
    category={query.get("category_id") || ""} sort={query.get("sort") || "updated_desc"}
    publicWebsiteUrl={publicWebsiteUrl || undefined} />;
}
