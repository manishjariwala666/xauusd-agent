import Link from "next/link";
import { notFound } from "next/navigation";
import { ArticleContent } from "@/components/article-content";
import { getContent, getContentDetail } from "@/lib/api";
export const revalidate = 300;
export async function generateStaticParams() { return (await getContent("PAGE", 12)).map((item) => ({ slug: item.slug })); }
export default async function StaticPage({ params }: { params: Promise<{ slug: string }> }) { const { slug } = await params; const item = await getContentDetail(slug); if (!item || item.content_type !== "PAGE") notFound(); return <article className="content-page"><nav className="breadcrumb" aria-label="Breadcrumb"><Link href="/">Home</Link><span>/</span><span>{item.title}</span></nav><header className="content-page-header"><span className="eyebrow">VENUSREALM</span><h1>{item.title}</h1>{item.excerpt && <p>{item.excerpt}</p>}</header><ArticleContent body={item.body || item.excerpt || "Page content is being prepared."} /></article>; }
