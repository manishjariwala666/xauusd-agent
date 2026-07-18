import Link from "next/link";
import { ContentGrid } from "./content-grid";
import type { ContentItem } from "@/lib/types";

export function BlogListing({ items, page = 1, totalPages }: { items: ContentItem[]; page?: number; totalPages?: number }) {
  const categories = Array.from(new Map(items.filter((item) => item.category_slug).map((item) => [item.category_slug, item.category_title || item.category_slug])).entries());
  return <>
    {categories.length > 0 && <nav className="category-filters" aria-label="Blog categories"><Link href="/blog">All research</Link>{categories.map(([slug, title]) => <Link href={`/category/${slug}`} key={slug}>{title}</Link>)}</nav>}
    <ContentGrid items={items} empty="No published market research is available yet." />
    {totalPages && totalPages > 1 ? <nav className="pagination" aria-label="Blog pagination">{page > 1 && <Link href={page === 2 ? "/blog" : `/blog/page/${page - 1}`}>Previous</Link>}{Array.from({ length: totalPages }, (_, index) => index + 1).map((number) => number === page ? <span className="current" aria-current="page" key={number}>{number}</span> : <Link href={number === 1 ? "/blog" : `/blog/page/${number}`} key={number}>{number}</Link>)}{page < totalPages && <Link href={`/blog/page/${page + 1}`}>Next</Link>}</nav> : items.length === 12 && <nav className="pagination" aria-label="Blog pagination"><Link href="/blog/page/2">More articles <span aria-hidden="true">→</span></Link></nav>}
  </>;
}
