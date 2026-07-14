import { notFound } from "next/navigation";
import { getContent, getContentDetail } from "@/lib/api";
export const revalidate = 300;
export async function generateStaticParams() { return (await getContent("ANNOUNCEMENT", 12)).map((item) => ({ slug: item.slug })); }
export default async function AnnouncementPage({ params }: { params: Promise<{ slug: string }> }) { const { slug } = await params; const item = await getContentDetail(slug); if (!item || item.content_type !== "ANNOUNCEMENT") notFound(); return <article className="article"><small>ANNOUNCEMENT</small><h1>{item.title}</h1><p className="lead">{item.excerpt}</p><div className="article-body">{(item.body || item.excerpt || "Update unavailable.").split("\n").filter(Boolean).map((p, i) => <p key={i}>{p}</p>)}</div></article>; }
