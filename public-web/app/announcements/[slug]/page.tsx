import Link from "next/link";
import { notFound } from "next/navigation";
import { ArticleContent } from "@/components/article-content";
import { ShareControls } from "@/components/share-controls";
import { getContent, getContentDetail, siteUrl } from "@/lib/api";
import { formatDate } from "@/lib/content";

export const revalidate = 300;
export async function generateStaticParams() { return (await getContent("ANNOUNCEMENT", 12)).map((item) => ({ slug: item.slug })); }
export default async function AnnouncementPage({ params }: { params: Promise<{ slug: string }> }) { const { slug } = await params; const item = await getContentDetail(slug); if (!item || item.content_type !== "ANNOUNCEMENT") notFound(); return <article className="article-shell"><nav className="breadcrumb" aria-label="Breadcrumb"><Link href="/">Home</Link><span>/</span><Link href="/announcements">Announcements</Link></nav><header className="article-header"><span className="eyebrow">ANNOUNCEMENT</span><h1>{item.title}</h1><p className="lead">{item.excerpt}</p><div className="article-meta"><time dateTime={item.published_at || item.created_at}>{formatDate(item.published_at || item.created_at)}</time></div></header><ShareControls title={item.title} url={siteUrl(`/announcements/${item.slug}`)} /><div className="article-layout"><div /><ArticleContent body={item.body || item.excerpt || "Update unavailable."} /></div></article>; }
