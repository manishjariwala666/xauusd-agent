import type { Metadata } from "next";
import Image from "next/image";
import { notFound } from "next/navigation";
import { getContentDetail, siteUrl } from "@/lib/api";

type Props = { params: Promise<{ slug: string }> };
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params; const item = await getContentDetail(slug);
  if (!item) return { title: "Article Not Found" };
  return { title: item.meta_title || item.title, description: item.meta_description || item.excerpt, alternates: { canonical: siteUrl(`/blog/${item.slug}`) }, openGraph: { type: "article", title: item.meta_title || item.title, description: item.meta_description || item.excerpt, url: siteUrl(`/blog/${item.slug}`), images: item.image_url ? [{ url: item.image_url, alt: `${item.title} featured image` }] : [] } };
}
export default async function BlogDetailPage({ params }: Props) {
  const { slug } = await params; const item = await getContentDetail(slug); if (!item) notFound();
  const schema = item.schema_jsonld || { "@context": "https://schema.org", "@type": "Article", headline: item.title, description: item.meta_description || item.excerpt, url: siteUrl(`/blog/${item.slug}`), datePublished: item.published_at || item.created_at };
  return <article className="article"><script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema).replace(/</g, "\\u003c") }} /><small>{item.category_title || "MARKET RESEARCH"}</small><h1>{item.title}</h1><p className="lead">{item.excerpt || "Public market research and risk context."}</p>{item.image_url ? <div className="article-image"><Image src={item.image_url} alt={`${item.title} featured image`} fill priority sizes="(max-width: 900px) 100vw, 900px" /></div> : <div className="article-fallback">AI MARKET ANALYTICS PRO</div>}<div className="article-body">{item.body ? item.body.split("\n").filter(Boolean).map((paragraph, index) => <p key={index}>{paragraph}</p>) : <p>This article is temporarily unavailable. Please return to the research library.</p>}</div></article>;
}
