import { notFound } from "next/navigation";
import { getContent, getContentDetail } from "@/lib/api";
export const revalidate = 300;
export async function generateStaticParams() { return (await getContent("PAGE", 12)).map((item) => ({ slug: item.slug })); }
export default async function StaticPage({ params }: { params: Promise<{ slug: string }> }) { const { slug } = await params; const item = await getContentDetail(slug); if (!item || item.content_type !== "PAGE") notFound(); return <article className="article"><small>AI MARKET ANALYTICS PRO</small><h1>{item.title}</h1><div className="article-body">{(item.body || item.excerpt || "Page content is being prepared.").split("\n").filter(Boolean).map((p, i) => <p key={i}>{p}</p>)}</div></article>; }
