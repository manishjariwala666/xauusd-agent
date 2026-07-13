import Link from "next/link";
import { ContentGrid } from "@/components/content-grid";
import { getCategories, getContent, getSignals } from "@/lib/api";

export default async function HomePage() {
  const [categories, blogs, announcements, signals] = await Promise.all([
    getCategories(), getContent(undefined, 6), getContent("ANNOUNCEMENT", 3), getSignals()
  ]);
  const publishedBlogs = blogs.filter((item) => ["BLOG", "AI_BLOG", "ANALYSIS", "EDUCATION", "ADVISORY"].includes(item.content_type));
  return <>
    <section className="hero"><small>MARKET INTELLIGENCE · RISK FIRST</small><h1>Clearer signals for gold and digital assets.</h1><p>Fast public research, structured XAUUSD levels and disciplined risk context—without loading private admin analytics.</p><div className="hero-actions"><Link className="button" href="/signals">View XAUUSD Signals</Link><Link className="button ghost" href="/blog">Explore Research</Link></div></section>
    <section><div className="section-heading"><div><small>LIVE DESK</small><h2>XAUUSD Signal Snapshot</h2></div><Link href="/signals">Open signal desk →</Link></div>{signals.length ? <div className="signal-strip">{signals.slice(0, 3).map((s, index) => <div key={s.id || index}><b>{s.signal_type || "WATCH"}</b><span>{s.symbol || "XAUUSD"}</span><strong>{s.price ?? "Live levels pending"}</strong></div>)}</div> : <div className="empty-state">Live signal data is temporarily unavailable. The page remains available.</div>}</section>
    <section><div className="section-heading"><div><small>EXPLORE</small><h2>Market Categories</h2></div></div><div className="category-grid">{(categories.length ? categories : [{slug:"xauusd-signals",title:"XAUUSD Signals",description:"Gold targets and risk context"},{slug:"analysis-department",title:"Market Analysis",description:"Technical and macro research"},{slug:"market-education",title:"Market Education",description:"Trading concepts and discipline"}]).map((category) => <Link href={`/category/${category.slug}`} key={category.slug}><span>{category.icon || "◆"}</span><h3>{category.title}</h3><p>{category.description || "Explore published market content."}</p></Link>)}</div></section>
    <section><div className="section-heading"><div><small>LATEST</small><h2>Research & Education</h2></div><Link href="/blog">View all →</Link></div><ContentGrid items={publishedBlogs} /></section>
    {announcements.length > 0 && <section><div className="section-heading"><div><small>UPDATES</small><h2>Announcements</h2></div></div><ContentGrid items={announcements} /></section>}
    <section className="risk"><b>Risk Disclaimer:</b> Market analysis and signals are informational only and never guarantee returns. Never risk capital you cannot afford to lose.</section>
  </>;
}
