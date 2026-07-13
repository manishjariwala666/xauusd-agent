import type { Metadata } from "next";
import { ContentGrid } from "@/components/content-grid";
import { getContent } from "@/lib/api";

export const metadata: Metadata = { title: "Market Blog", description: "Published XAUUSD research, market analysis and trading education." };
export default async function BlogPage() {
  const items = (await getContent(undefined, 60)).filter((item) => ["BLOG", "AI_BLOG", "ADVISORY", "ANALYSIS", "EDUCATION"].includes(item.content_type));
  return <section><div className="page-heading"><small>RESEARCH LIBRARY</small><h1>Market Blog</h1><p>SEO-ready, risk-aware XAUUSD and market education.</p></div><ContentGrid items={items} /></section>;
}
