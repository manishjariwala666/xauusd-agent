import { notFound } from "next/navigation";
import { getContentDetail } from "@/lib/api";
export default async function StaticPage({ params }: { params: Promise<{ slug: string }> }) { const { slug } = await params; const item = await getContentDetail(slug); if (!item || item.content_type !== "PAGE") notFound(); return <article className="article"><small>AI MARKET ANALYTICS PRO</small><h1>{item.title}</h1><div className="article-body">{(item.body || item.excerpt || "Page content is being prepared.").split("\n").filter(Boolean).map((p, i) => <p key={i}>{p}</p>)}</div></article>; }
