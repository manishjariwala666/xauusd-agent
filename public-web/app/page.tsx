import Image from "next/image";
import Link from "next/link";
import { FaqItem, InsightCard, ResearchToolCard, SnapshotItem } from "@/components/homepage-sections";
import { ContentGrid } from "@/components/content-grid";
import { Icon, type IconName } from "@/components/icon";
import { getContent, getResultSnapshot } from "@/lib/api";
import { configuredLinks } from "@/lib/site-config";

export const revalidate = 300;

const tools: { icon: IconName; title: string; text: string; href: string }[] = [
  { icon: "chart", title: "Market analysis", text: "Technical and macro research designed to reduce noise and improve context.", href: "/category/analysis-department" },
  { icon: "moon", title: "Financial astrology", text: "A supplementary educational timing lens used alongside structure and risk.", href: "/astrology" },
  { icon: "book", title: "Market learning", text: "Practical education focused on process, discipline and risk control.", href: "/category/market-education" },
  { icon: "brain", title: "AI research", text: "AI-assisted synthesis with explicit uncertainty and editorial review.", href: "/blog" },
];

const deliverables = [
  ["01", "Premium Signal Desk", "Protected XAUUSD signal data is requested only after verified paid-member access."],
  ["02", "Research briefs", "Structured XAUUSD analysis separating facts, interpretation and uncertainty."],
  ["03", "Risk framework", "Invalidation and risk framing stay visible before any upside narrative."],
  ["04", "Verified results", "Only evidence-backed, compliance-safe public records are eligible."],
  ["05", "Fast alerts", "Approved updates can reach configured channels without becoming the source of truth."],
  ["06", "Member access", "Secure account and verification flows keep protected content separated from public pages."],
];

const modules = [
  ["Premium Signal Desk", "Paid-member XAUUSD signal detail stays behind authenticated, verified access.", "/signals"],
  ["Market research", "Editorial XAUUSD analysis, education and desk commentary.", "/blog"],
  ["Evidence layer", "Verified public results with privacy and publication controls.", "/results"],
  ["Timing research", "Financial astrology framed only as supplementary context.", "/astrology"],
];

function isPresentableResearch(item: { title?: string | null; content_type: string }) {
  const title = (item.title || "").trim();
  if (title.length < 6) return false;
  return !/^(a+|test(?:ing)?|demo|sample|untitled|draft)$/i.test(title);
}

export default async function HomePage() {
  const [content, results] = await Promise.all([getContent(undefined, 12), getResultSnapshot()]);
  const publishedBlogs = content
    .filter((item) => ["BLOG", "AI_BLOG", "ANALYSIS", "EDUCATION", "ADVISORY"].includes(item.content_type))
    .filter(isPresentableResearch)
    .slice(0, 6);
  const latest = publishedBlogs[0];
  const links = configuredLinks();
  const researchTools = links.telegram ? [...tools, { icon: "send" as IconName, title: "Telegram alerts", text: "Configured public research updates and alerts delivered through the official channel.", href: links.telegram }] : tools;
  const updateTime = latest?.published_at || latest?.created_at;

  return <div className="home-page">
    <section className="home-hero">
      <Image className="home-hero-art" src="/images/home/venusrealm-gold-desk-hero.png" alt="Gold bars and market charts inside a premium commodities research desk" fill priority sizes="(max-width: 760px) 100vw, 1240px" />
      <span className="home-hero-shade" aria-hidden="true" />
      <div className="home-hero-copy"><span className="eyebrow"><span />Independent gold intelligence</span><h1>Read gold with <em>clarity.</em><br />Act with discipline.</h1><p>VenusRealm combines XAUUSD research, timing context and AI-assisted analysis with a protected Gold Signal Desk for verified paid members.</p><div className="hero-actions"><Link className="button button-gold" href="/signals">Premium Signal Desk <Icon name="arrow" size={18} /></Link><Link className="button home-button-outline" href="/blog">Read latest research</Link></div><div className="home-hero-proof" aria-label="Research principles"><span><Icon name="shield" size={15} />Signal data protected</span><span><Icon name="brain" size={15} />AI-assisted, reviewed</span><span><Icon name="book" size={15} />Education, not advice</span></div></div>
      <aside className="terminal-panel" aria-label="VenusRealm research desk principles"><div className="terminal-topline"><span><i /> Research desk</span><small>Public intelligence</small></div><div className="terminal-market"><div><small>Primary market</small><strong>XAUUSD</strong></div><span className="terminal-status">Risk-first</span></div><div className="terminal-chart" aria-hidden="true"><span className="chart-line" /><span className="chart-marker marker-a" /><span className="chart-marker marker-b" /></div><div className="terminal-principles"><InsightCard index="01" label="Structure" value="Before signal" /><InsightCard index="02" label="Context" value="Before conviction" /><InsightCard index="03" label="Risk" value="Before reward" /></div><p>Live Gold Signal data is not requested or rendered on the public homepage.</p></aside>
    </section>

    <section className="desk-strip" aria-labelledby="snapshot-title"><div className="desk-strip-heading"><div><span className="eyebrow">Desk at a glance</span><h2 id="snapshot-title">Clear access. Clear boundaries.</h2></div><span className="data-note"><Icon name="shield" size={15} />Protected member data</span></div><div className="desk-snapshot-grid"><SnapshotItem label="Gold Signal Desk" value="Paid members only" detail="Live signal data stays behind verified member access" href="/signals" /><SnapshotItem label="Protected data" value="Direction · Entry · SL · Targets" detail="Never rendered on this public homepage" href="/signals" /><SnapshotItem label="Latest research" value={latest?.title || "Research library"} detail={latest?.category_title || "Published editorial research"} href={latest ? `/blog/${latest.slug}` : "/blog"} /><SnapshotItem label="Research update" value={formatUpdateTime(updateTime)} detail="Public editorial content only" /></div></section>

    <section className="home-section home-deliverables" aria-labelledby="deliverables-title"><header className="editorial-heading"><div><span className="eyebrow">What you get</span><h2 id="deliverables-title">A focused research system, not a wall of features.</h2></div><p>Six clear layers cover the journey from public research to protected paid-member access.</p></header><div className="deliverable-grid">{deliverables.map(([number, title, text]) => <article key={number}><span>{number}</span><h3>{title}</h3><p>{text}</p></article>)}</div></section>

    <section className="premium-signal-showcase" aria-labelledby="premium-signal-title">
      <div className="premium-signal-showcase-art"><Image src="/images/home/venusrealm-gold-desk-hero.png" alt="VenusRealm premium Gold Signal Desk" fill sizes="(max-width: 760px) 100vw, 48vw" /><span aria-hidden="true" /></div>
      <div className="premium-signal-showcase-copy"><span className="eyebrow">Premium Gold Signal Desk</span><h2 id="premium-signal-title">The signal is a member product—not a public post.</h2><p>Visitors can understand what the service provides, but live signal data is loaded only inside the verified paid-member flow. The public website does not display direction, timeframe, entry, stop-loss, targets or signal timestamps.</p><div className="premium-signal-locks"><span><Icon name="shield" size={17} /><b>Direction</b><small>Protected</small></span><span><Icon name="shield" size={17} /><b>Entry + SL</b><small>Protected</small></span><span><Icon name="shield" size={17} /><b>Targets</b><small>Protected</small></span></div><div className="hero-actions"><Link className="button button-gold" href="/signals">Open member desk <Icon name="arrow" size={17} /></Link><Link className="button home-button-outline" href="/login">Member login</Link></div></div>
    </section>

    <section className="home-section home-tools" aria-labelledby="tools-title"><header className="editorial-heading"><div><span className="eyebrow">Public research</span><h2 id="tools-title">Research visitors can explore freely.</h2></div><p>These public capabilities provide educational context without exposing protected Gold Signal data.</p></header><div className="research-tool-grid">{researchTools.map((tool, index) => <ResearchToolCard {...tool} index={index + 1} key={tool.title} />)}</div></section>

    <section className="home-section modules-section" aria-labelledby="modules-title"><div className="module-visual"><Image src="/images/home/venusrealm-gold-desk-hero.png" alt="Gold research desk visual" fill sizes="(max-width: 760px) 100vw, 44vw" /></div><div className="module-copy"><span className="eyebrow">How the desk is organised</span><h2 id="modules-title">Four modules. One clear research journey.</h2><p>Visitors should always understand what is public and what requires verified paid-member access.</p><div className="module-list">{modules.map(([title, text, href], index) => <Link href={href} key={title}><span>0{index + 1}</span><div><strong>{title}</strong><small>{text}</small></div><Icon name="arrow" size={18} /></Link>)}</div></div></section>

    <section className="home-section research-section" aria-labelledby="analysis-title"><header className="editorial-heading"><div><span className="eyebrow">Latest research</span><h2 id="analysis-title">Read the reasoning behind the market.</h2></div><Link className="text-link" href="/blog">Browse all research <Icon name="arrow" size={16} /></Link></header><ContentGrid items={publishedBlogs} /></section>

    <section className="proof-section" aria-labelledby="results-title"><div className="proof-copy"><span className="eyebrow">Evidence over assertion</span><h2 id="results-title">Proof should be documented,<br />not promised.</h2><p>Only evidence-backed, redacted, compliance-approved records are eligible. VenusRealm does not infer ROI, account profit or unverified win rates.</p><Link className="text-link" href="/results">Read methodology and records <Icon name="arrow" size={16} /></Link></div><div className="proof-card"><span className="proof-seal"><Icon name="target" size={26} /></span><small>Verified public record</small>{results.length ? <><strong>{results[0].symbol} {results[0].direction}</strong><span>{results[0].result_points} {results[0].result_unit}</span><p>{results[0].public_summary}</p></> : <><strong>Awaiting verified records</strong><p>No synthetic claims or placeholder percentages are shown.</p></>}</div></section>

    <section className="home-section faq-section" aria-labelledby="faq-title"><header className="editorial-heading faq-heading"><div><span className="eyebrow">FAQ</span><h2 id="faq-title">The important questions, answered clearly.</h2></div><p>Access, risk and public-versus-protected information should never be confusing.</p></header><div className="editorial-faq"><FaqItem number="01" question="Can public visitors see Gold Signal data?">No. Live Gold Signal data is reserved for verified paid members and is not requested by the public homepage or public Signals page.</FaqItem><FaqItem number="02" question="What is protected?">Signal direction, timeframe, entry, stop-loss, targets and live signal timestamps remain inside the authenticated paid-member flow.</FaqItem><FaqItem number="03" question="How do member signals work?">A valid member session and verified paid-access state are required before protected signal detail is requested.</FaqItem><FaqItem number="04" question="How are results presented?">Only evidence-backed public records that pass privacy and publication controls are shown.</FaqItem><FaqItem number="05" question="What are the risks?">Gold and leveraged markets can move quickly. Past results do not predict future outcomes, and no signal guarantees a result.</FaqItem></div></section>
  </div>;
}

function formatUpdateTime(value: string | undefined) {
  if (!value) return "No recent post";
  return new Intl.DateTimeFormat("en", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}
