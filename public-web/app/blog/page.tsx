import type { Metadata } from "next";
import { BlogListing } from "@/components/blog-listing";
import { getContent } from "@/lib/api";
import { articleItems } from "@/lib/content";

export const metadata: Metadata = { title: "Market Blog", description: "Published XAUUSD research, market analysis and trading education." };
export const revalidate = 300;
export default async function BlogPage() {
  const items = articleItems(await getContent(undefined, 12));
  return <section><header className="page-heading"><span className="eyebrow">VENUSREALM JOURNAL</span><h1>Gold market research, without the noise.</h1><p>Explore XAUUSD structure, macro context, disciplined risk and AI-assisted market education. Every card is metadata-only; full articles load only when opened.</p></header><BlogListing items={items} /></section>;
}
