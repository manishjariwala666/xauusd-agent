import { notFound } from "next/navigation";
import { BlogListing } from "@/components/blog-listing";
import { getContent } from "@/lib/api";
import { articleItems, PAGE_SIZE } from "@/lib/content";

export const revalidate = 300;
export async function generateStaticParams() { const count = articleItems(await getContent(undefined, 100)).length; return Array.from({ length: Math.max(0, Math.ceil(count / PAGE_SIZE) - 1) }, (_, index) => ({ page: String(index + 2) })); }

export default async function BlogPaginationPage({ params }: { params: Promise<{ page: string }> }) {
  const page = Number((await params).page);
  const all = articleItems(await getContent(undefined, 100));
  const totalPages = Math.ceil(all.length / PAGE_SIZE);
  if (!Number.isInteger(page) || page < 2 || page > totalPages) notFound();
  const items = all.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  return <section><header className="page-heading"><span className="eyebrow">VENUSREALM JOURNAL</span><h1>Market research archive.</h1><p>Page {page} of published gold analysis and educational research.</p></header><BlogListing items={items} page={page} totalPages={totalPages} /></section>;
}
