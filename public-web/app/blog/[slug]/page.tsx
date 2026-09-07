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
import { isSparseResearchBody, researchVisual } from "@/lib/research-visual";

type Props = { params: Promise<{ slug: string }> };

type Faq = { question: string; answer: string };

export const revalidate = 300;

export async function generateStaticParams() {
  const items = await getContent(undefined, 12);
  return items.filter((item) => ARTICLE_TYPES.includes(item.content_type)).map((item) => ({ slug: item.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const item = await getContentDetail(slug);
  if (!item) return { title: "Article Not Found" };
  const visual = researchVisual(item);
  return {
    title: item.meta_title || item.title,
    description: item.meta_description || item.excerpt || `VenusRealm research on ${item.title}, XAUUSD market structure and disciplined risk.` ,
    alternates: { canonical: siteUrl(`/blog/${item.slug}`) },
    openGraph: {
      type: "article",
      title: item.meta_title || item.title,
      description: item.meta_description || item.excerpt,
      url: siteUrl(`/blog/${item.slug}`),
      images: [{ url: siteUrl(visual), alt: `${item.title} featured research visual` }],
    },
  };
}

function researchFaqs(title: string): Faq[] {
  const lower = title.toLowerCase();
  if (lower.includes("ai")) return [
    { question: "How does AI support XAUUSD research?", answer: "AI can help organize market inputs, compare scenarios and summarize recurring themes. VenusRealm treats it as an assisted research layer rather than an autonomous trading authority." },
    { question: "Does AI generate guaranteed Gold signals?", answer: "No. Market outcomes remain uncertain. AI-assisted analysis must be interpreted with market structure, risk controls and human review." },
    { question: "What should traders verify before acting on AI-assisted analysis?", answer: "Check price structure, invalidation conditions, macro context, liquidity and personal risk limits before considering any trade." },
  ];
  if (lower.includes("astro") || lower.includes("timing") || lower.includes("cycle")) return [
    { question: "Is financial astrology a standalone trading signal?", answer: "No. VenusRealm presents timing cycles only as supplementary educational context alongside market structure, macro information and risk management." },
    { question: "What matters more than a timing cycle?", answer: "Price structure, invalidation, liquidity and disciplined position risk remain primary. Timing observations do not guarantee direction or outcome." },
    { question: "How can timing research be used responsibly?", answer: "Use it to frame questions and observation windows, then require confirmation from conventional market evidence before making decisions." },
  ];
  return [
    { question: "What is XAUUSD market structure?", answer: "Market structure describes how gold price forms trends, ranges, swing highs, swing lows, support and resistance. It helps traders organize price action before considering a setup." },
    { question: "Why is invalidation important in Gold trading?", answer: "Invalidation defines the condition that proves a trade idea is no longer working as expected. Clear invalidation supports disciplined risk control and reduces emotional decision-making." },
    { question: "Does this research provide financial advice?", answer: "No. VenusRealm research is educational information. Gold and leveraged markets involve substantial risk, and no analysis or signal can guarantee an outcome." },
  ];
}

export default async function BlogDetailPage({ params }: Props) {
  const { slug } = await params;
  const [item, summaries] = await Promise.all([getContentDetail(slug), getContent(undefined, 12)]);
  if (!item) notFound();

  const visual = researchVisual(item);
  const faqs = researchFaqs(item.title);
  const articleSchema = item.schema_jsonld || {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: item.title,
    description: item.meta_description || item.excerpt,
    image: siteUrl(visual),
    url: siteUrl(`/blog/${item.slug}`),
    datePublished: item.published_at || item.created_at,
    author: { "@type": "Organization", name: item.author_name || item.author || "VenusRealm Research Desk" },
  };
  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((faq) => ({ "@type": "Question", name: faq.question, acceptedAnswer: { "@type": "Answer", text: faq.answer } })),
  };
  const breadcrumb = { "@context": "https://schema.org", "@type": "BreadcrumbList", itemListElement: [{ "@type": "ListItem", position: 1, name: "Home", item: siteUrl() }, { "@type": "ListItem", position: 2, name: "Blog", item: siteUrl("/blog") }, { "@type": "ListItem", position: 3, name: item.title, item: siteUrl(`/blog/${item.slug}`) }] };
  const articles = articleItems(summaries);
  const currentIndex = articles.findIndex((candidate) => candidate.slug === item.slug);
  const related = articles.filter((candidate) => candidate.slug !== item.slug && (!item.category_slug || candidate.category_slug === item.category_slug)).slice(0, 3);
  const previous = currentIndex >= 0 ? articles[currentIndex + 1] : undefined;
  const next = currentIndex > 0 ? articles[currentIndex - 1] : undefined;
  const toc = parseArticle(item.body || "").toc;
  const published = item.published_at || item.created_at;
  const sparse = isSparseResearchBody(item.body);

  return <article className="article-shell">
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(articleSchema).replace(/</g, "\\u003c") }} />
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema).replace(/</g, "\\u003c") }} />
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumb).replace(/</g, "\\u003c") }} />
    <nav className="breadcrumb" aria-label="Breadcrumb"><Link href="/">Home</Link><span>/</span><Link href="/blog">Blog</Link><span>/</span><span aria-current="page">{item.category_title || "Research"}</span></nav>
    <header className="article-header"><span className="eyebrow">{item.category_title || "MARKET RESEARCH"}</span><h1>{item.title}</h1><p className="lead">{item.excerpt || "Public XAUUSD market research focused on structure, context and disciplined risk."}</p><div className="article-meta"><span><Icon name="brain" size={15} />{item.author_name || item.author || "VenusRealm Research Desk"}</span><span><Icon name="clock" size={15} />{formatDate(published)}</span><span>{Math.max(readingMinutes(item.body), sparse ? 4 : 1)} min read</span></div></header>
    <div className="article-image"><Image src={visual} alt={`${item.title} featured research visual`} fill priority sizes="(max-width: 1100px) 100vw, 1040px" /></div>
    <ShareControls title={item.title} url={siteUrl(`/blog/${item.slug}`)} />
    {sparse && <section className="article-context-brief" aria-labelledby="research-context-title"><span className="eyebrow">RESEARCH CONTEXT</span><h2 id="research-context-title">What this article helps you evaluate.</h2><p>Use this research to organize the market, not to predict it with certainty. A disciplined XAUUSD process starts with structure, checks the surrounding context, defines invalidation and only then considers opportunity.</p><div className="article-context-grid"><div><strong>01 · Structure</strong><span>Identify trend, range, support, resistance and important swing points.</span></div><div><strong>02 · Context</strong><span>Compare technical evidence with macro drivers, liquidity and current volatility.</span></div><div><strong>03 · Risk</strong><span>Define what would invalidate the idea before focusing on potential reward.</span></div></div></section>}
    <div className="article-layout">{toc.length > 1 ? <nav className="table-of-contents" aria-label="Table of contents"><strong>In this article</strong>{toc.map((heading) => <a data-level={heading.level} href={`#${heading.id}`} key={`${heading.level}-${heading.id}`}>{heading.label}</a>)}</nav> : <div />}<ArticleContent body={item.body || "XAUUSD research should begin with observable price structure, then add macro and timing context while keeping invalidation and risk limits explicit. VenusRealm does not treat any single indicator, narrative or model as sufficient on its own."} /></div>
    <section className="article-faq" aria-labelledby="article-faq-title"><span className="eyebrow">FAQ</span><h2 id="article-faq-title">Common questions about this research.</h2><div>{faqs.map((faq) => <details key={faq.question}><summary>{faq.question}<span aria-hidden="true">+</span></summary><p>{faq.answer}</p></details>)}</div></section>
    <div className="article-risk risk"><strong>Risk disclaimer:</strong> This material is educational and not financial advice. Gold and leveraged markets involve substantial risk, and no analysis can guarantee an outcome.</div>
    {(previous || next) && <nav className="article-navigation" aria-label="Previous and next articles">{previous ? <Link href={`/blog/${previous.slug}`}><span>Previous article</span><strong>{previous.title}</strong></Link> : <span />}{next && <Link href={`/blog/${next.slug}`}><span>Next article</span><strong>{next.title}</strong></Link>}</nav>}
    {related.length > 0 && <section className="related-section"><div className="section-heading compact-heading"><div><span className="eyebrow">CONTINUE READING</span><h2>Related market research.</h2></div></div><ContentGrid compact items={related} /></section>}
  </article>;
}
