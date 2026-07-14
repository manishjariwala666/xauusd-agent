import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getContent, getContentDetail, siteUrl } from "@/lib/api";
import { ArticleContent, parseArticle } from "@/components/article-content";
import { ContentGrid } from "@/components/content-grid";
import { Icon } from "@/components/icon";
import { ShareControls } from "@/components/share-controls";
import { articleItems, ARTICLE_TYPES, formatDate, readingMinutes } from "@/lib/content";

type Props = { params: Promise<{ slug: string }> };

export const revalidate = 300;

export async function generateStaticParams() {
  const items = await getContent(undefined, 12);
  return items.filter((item) => ARTICLE_TYPES.includes(item.content_type)).map((item) => ({ slug: item.slug }));
}
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params; const item = await getContentDetail(slug);
  if (!item) return { title: "Article Not Found" };
  return { title: item.meta_title || item.title, description: item.meta_description || item.excerpt, alternates: { canonical: siteUrl(`/blog/${item.slug}`) }, openGraph: { type: "article", title: item.meta_title || item.title, description: item.meta_description || item.excerpt, url: siteUrl(`/blog/${item.slug}`), images: item.image_url ? [{ url: item.image_url, alt: `${item.title} featured image` }] : [] } };
}
export default async function BlogDetailPage({ params }: Props) {
  const { slug } = await params; const [item, summaries] = await Promise.all([getContentDetail(slug), getContent(undefined, 12)]); if (!item) notFound();
  const schema = item.schema_jsonld || { "@context": "https://schema.org", "@type": "Article", headline: item.title, description: item.meta_description || item.excerpt, url: siteUrl(`/blog/${item.slug}`), datePublished: item.published_at || item.created_at };
  const breadcrumb = { "@context": "https://schema.org", "@type": "BreadcrumbList", itemListElement: [{ "@type": "ListItem", position: 1, name: "Home", item: siteUrl() }, { "@type": "ListItem", position: 2, name: "Blog", item: siteUrl("/blog") }, { "@type": "ListItem", position: 3, name: item.title, item: siteUrl(`/blog/${item.slug}`) }] };
  const articles = articleItems(summaries);
  const currentIndex = articles.findIndex((candidate) => candidate.slug === item.slug);
  const related = articles.filter((candidate) => candidate.slug !== item.slug && (!item.category_slug || candidate.category_slug === item.category_slug)).slice(0, 3);
  const previous = currentIndex >= 0 ? articles[currentIndex + 1] : undefined;
  const next = currentIndex > 0 ? articles[currentIndex - 1] : undefined;
  const toc = parseArticle(item.body || "").toc;
  const published = item.published_at || item.created_at;
  return <article className="article-shell"><script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema).replace(/</g, "\\u003c") }} /><script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumb).replace(/</g, "\\u003c") }} />
    <nav className="breadcrumb" aria-label="Breadcrumb"><Link href="/">Home</Link><span>/</span><Link href="/blog">Blog</Link><span>/</span><span aria-current="page">{item.category_title || "Research"}</span></nav>
    <header className="article-header"><span className="eyebrow">{item.category_title || "MARKET RESEARCH"}</span><h1>{item.title}</h1><p className="lead">{item.excerpt || "Public market research and risk context."}</p><div className="article-meta"><span><Icon name="brain" size={15} />{item.author_name || item.author || "VenusRealm Research Desk"}</span><span><Icon name="clock" size={15} />{formatDate(published)}</span><span>{readingMinutes(item.body)} min read</span></div></header>
    {item.image_url ? <div className="article-image"><Image src={item.image_url} alt={`${item.title} featured image`} fill priority sizes="(max-width: 1100px) 100vw, 1040px" /></div> : <div className="article-fallback"><div className="article-fallback-inner"><Icon name="gold" size={42}/><span>VENUSREALM GOLD RESEARCH</span></div></div>}
    <ShareControls title={item.title} url={siteUrl(`/blog/${item.slug}`)} />
    <div className="article-layout">{toc.length > 1 ? <nav className="table-of-contents" aria-label="Table of contents"><strong>In this article</strong>{toc.map((heading) => <a data-level={heading.level} href={`#${heading.id}`} key={`${heading.level}-${heading.id}`}>{heading.label}</a>)}</nav> : <div />}<ArticleContent body={item.body || "This article is temporarily unavailable. Please return to the research library."} /></div>
    <div className="article-risk risk"><strong>Risk disclaimer:</strong> This material is educational and not financial advice. Gold and leveraged markets involve substantial risk, and no analysis can guarantee an outcome.</div>
    {(previous || next) && <nav className="article-navigation" aria-label="Previous and next articles">{previous ? <Link href={`/blog/${previous.slug}`}><span>Previous article</span><strong>{previous.title}</strong></Link> : <span />}{next && <Link href={`/blog/${next.slug}`}><span>Next article</span><strong>{next.title}</strong></Link>}</nav>}
    {related.length > 0 && <section className="related-section"><div className="section-heading compact-heading"><div><span className="eyebrow">CONTINUE READING</span><h2>Related market research.</h2></div></div><ContentGrid compact items={related} /></section>}
  </article>;
}
