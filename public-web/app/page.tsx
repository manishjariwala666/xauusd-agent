import Image from "next/image";
import Link from "next/link";
import { FaqItem, InsightCard, ResearchToolCard, SnapshotItem } from "@/components/homepage-sections";
import { ContentGrid } from "@/components/content-grid";
import { Icon, type IconName } from "@/components/icon";
import { getContent, getResultSnapshot, getSignalSnapshot } from "@/lib/api";
import { configuredLinks } from "@/lib/site-config";

export const revalidate = 300;

const tools: { icon: IconName; title: string; text: string; href: string }[] = [
  { icon: "gold", title: "Gold signals", text: "Structured XAUUSD context with protected member-only trade levels.", href: "/signals" },
  { icon: "chart", title: "Market analysis", text: "Technical and macro research designed to reduce noise and improve context.", href: "/category/analysis-department" },
  { icon: "moon", title: "Financial astrology", text: "A supplementary educational timing lens used alongside structure and risk.", href: "/astrology" },
  { icon: "book", title: "Market learning", text: "Practical education focused on process, discipline and risk control.", href: "/category/market-education" },
  { icon: "brain", title: "AI research", text: "AI-assisted synthesis with explicit uncertainty and editorial review.", href: "/blog" },
];

const deliverables = [
  ["01", "Signal desk", "Public teaser context with protected detail for verified members."],
  ["02", "Research briefs", "Structured XAUUSD analysis separating facts, interpretation and uncertainty."],
  ["03", "Risk framework", "Invalidation and risk framing stay visible before any upside narrative."],
  ["04", "Verified results", "Only evidence-backed, compliance-safe public records are eligible."],
  ["05", "Fast alerts", "Approved updates can reach configured channels without becoming the source of truth."],
  ["06", "Member access", "Secure account and verification flows keep protected content separated from public pages."],
];

const modules = [
  ["Signal intelligence", "Public status and protected member detail remain clearly separated.", "/signals"],
  ["Market research", "Editorial XAUUSD analysis, education and desk commentary.", "/blog"],
  ["Evidence layer", "Verified public results with privacy and publication controls.", "/results"],
  ["Timing research", "Financial astrology framed only as supplementary context.", "/astrology"],
];

export default async function HomePage() {
  const [content, signals, results] = await Promise.all([getContent(undefined, 12), getSignalSnapshot(), getResultSnapshot()]);
  const publishedBlogs = content.filter((item) => ["BLOG", "AI_BLOG", "ANALYSIS", "EDUCATION", "ADVISORY"].includes(item.content_type)).slice(0, 6);
  const latest = publishedBlogs[0];
  const signal = signals[0];
  const links = configuredLinks();
  const researchTools = links.telegram ? [...tools, { icon: "send" as IconName, title: "Telegram alerts", text: "Fast delivery when a verified public alert is available.", href: links.telegram }] : tools;
  const updateTime = signal?.updated_at || signal?.published_at || signal?.signal_time || latest?.published_at || latest?.created_at;

  return <div className="home-page">
    <section className="home-hero">
      <Image className="home-hero-art" src="/images/home/venusrealm-gold-desk-hero.png" alt="Gold bars and market charts inside a premium commodities research desk" fill priority sizes="(max-width: 760px) 100vw, 1240px" />
      <span className="home-hero-shade" aria-hidden="true" />
      <div className="home-hero-copy"><span className="eyebrow"><span />Independent gold intelligence</span><h1>Read gold with <em>clarity.</em><br />Act with discipline.</h1><p>VenusRealm combines XAUUSD signals, market structure, timing research and AI-assisted analysis inside one risk-first research desk.</p><div className="hero-actions"><Link className="button button-gold" href="/signals">Enter the signal desk <Icon name="arrow" size={18} /></Link><Link className="button home-button-outline" href="/blog">Read latest research</Link></div><div className="home-hero-proof" aria-label="Research principles"><span><Icon name="shield" size={15} />Risk before reward</span><span><Icon name="brain" size={15} />AI-assisted, reviewed</span><span><Icon name="book" size={15} />Education, not advice</span></div></div>
      <aside className="terminal-panel" aria-label="VenusRealm research desk principles"><div className="terminal-topline"><span><i /> Research desk</span><small>Public intelligence</small></div><div className="terminal-market"><div><small>Primary market</small><strong>XAUUSD</strong></div><span className="terminal-status">Risk-first</span></div><div className="terminal-chart" aria-hidden="true"><span className="chart-line" /><span className="chart-marker marker-a" /><span className="chart-marker marker-b" /></div><div className="terminal-principles"><InsightCard index="01" label="Structure" value="Before signal" /><InsightCard index="02" label="Context" value="Before conviction" /><InsightCard index="03" label="Risk" value="Before reward" /></div><p>Public research and protected member detail remain intentionally separate.</p></aside>
    </section>

    <section className="desk-strip" aria-labelledby="snapshot-title"><div className="desk-strip-heading"><div><span className="eyebrow">Desk at a glance</span><h2 id="snapshot-title">What the desk knows now.</h2></div><span className="data-note"><span className="status-dot" />Cached public data</span></div><div className="desk-snapshot-grid"><SnapshotItem label="XAUUSD status" value={signal?.signal_type || "No verified signal"} detail={signal?.symbol || "Awaiting a published market row"} /><SnapshotItem label="Signal access" value={signal ? "Published teaser" : "No active teaser"} detail={signal?.timeframe ? `${signal.timeframe} context available` : "Open the signal desk for public context"} href="/signals" /><SnapshotItem label="Latest analysis" value={latest?.title || "Research unavailable"} detail={latest?.category_title || "Published editorial research"} href={latest ? `/blog/${latest.slug}` : "/blog"} /><SnapshotItem label="Last public update" value={formatUpdateTime(updateTime)} detail="Published public data" /></div></section>

    <section className="home-section home-deliverables" aria-labelledby="deliverables-title"><header className="editorial-heading"><div><span className="eyebrow">What you get</span><h2 id="deliverables-title">A focused research system, not a wall of features.</h2></div><p>Six clear layers cover the visitor journey from public context to protected member access.</p></header><div className="deliverable-grid">{deliverables.map(([number, title, text]) => <article key={number}><span>{number}</span><h3>{title}</h3><p>{text}</p></article>)}</div></section>

    <section className="home-section home-tools" aria-labelledby="tools-title"><header className="editorial-heading"><div><span className="eyebrow">Research capabilities</span><h2 id="tools-title">The tools that matter.<br /><em>Nothing decorative.</em></h2></div><p>Each capability has a specific role in understanding gold, risk and market context.</p></header><div className="research-tool-grid">{researchTools.map((tool, index) => <ResearchToolCard {...tool} index={index + 1} key={tool.title} />)}</div></section>

    <section className="home-section modules-section" aria-labelledby="modules-title"><div className="module-visual"><Image src="/images/home/venusrealm-gold-desk-hero.png" alt="Gold research desk visual" fill sizes="(max-width: 760px) 100vw, 44vw" /></div><div className="module-copy"><span className="eyebrow">How the desk is organised</span><h2 id="modules-title">Four modules. One clear research journey.</h2><p>Visitors should always understand where they are, what they can see and what remains protected.</p><div className="module-list">{modules.map(([title, text, href], index) => <Link href={href} key={title}><span>0{index + 1}</span><div><strong>{title}</strong><small>{text}</small></div><Icon name="arrow" size={18} /></Link>)}</div></div></section>

    <section className="levels-section" aria-labelledby="signals-title"><header className="levels-heading"><div><span className="eyebrow">Signal desk</span><h2 id="signals-title">Public context.<br />Protected levels.</h2></div><div><p>The homepage stays non-actionable. Entry, stop-loss and targets remain inside the protected signal access flow.</p><Link className="text-link" href="/signals">Open signal desk <Icon name="arrow" size={16} /></Link></div></header>{signals.length ? <div className="premium-signal-grid">{signals.slice(0, 3).map((item, index) => <article className="premium-signal-card" key={item.id || index}><div className="signal-card-head"><span>{item.symbol || "XAUUSD"}</span><b>{item.signal_type || "WATCH"}</b></div><dl><div><dt>Timeframe</dt><dd>{item.timeframe || "—"}</dd></div><div><dt>Status</dt><dd>Published</dd></div><div><dt>Risk levels</dt><dd>Protected</dd></div><div><dt>Access</dt><dd><Link href="/signals">Open desk</Link></dd></div></dl></article>)}</div> : <div className="levels-empty"><span className="levels-empty-mark"><Icon name="clock" size={24} /></span><div><small>Desk status</small><h3>No verified signal is currently published.</h3><p>Public context appears only after a signal clears the publishing workflow.</p></div></div>}</section>

    <section className="home-section research-section" aria-labelledby="analysis-title"><header className="editorial-heading"><div><span className="eyebrow">Latest research</span><h2 id="analysis-title">Read the reasoning behind the market.</h2></div><Link className="text-link" href="/blog">Browse all research <Icon name="arrow" size={16} /></Link></header><ContentGrid items={publishedBlogs} /></section>

    <section className="proof-section" aria-labelledby="results-title"><div className="proof-copy"><span className="eyebrow">Evidence over assertion</span><h2 id="results-title">Proof should be documented,<br />not promised.</h2><p>Only evidence-backed, redacted, compliance-approved records are eligible. VenusRealm does not infer ROI, account profit or unverified win rates.</p><Link className="text-link" href="/results">Read methodology and records <Icon name="arrow" size={16} /></Link></div><div className="proof-card"><span className="proof-seal"><Icon name="target" size={26} /></span><small>Verified public record</small>{results.length ? <><strong>{results[0].symbol} {results[0].direction}</strong><span>{results[0].result_points} {results[0].result_unit}</span><p>{results[0].public_summary}</p></> : <><strong>Awaiting verified records</strong><p>No synthetic claims or placeholder percentages are shown.</p></>}</div></section>

    <section className="home-section faq-section" aria-labelledby="faq-title"><header className="editorial-heading faq-heading"><div><span className="eyebrow">FAQ</span><h2 id="faq-title">The important questions, answered clearly.</h2></div><p>Access, risk and public-versus-protected information should never be confusing.</p></header><div className="editorial-faq"><FaqItem number="01" question="Are signals financial advice?">No. Signals and analysis are educational information and do not account for your circumstances.</FaqItem><FaqItem number="02" question="What can a public visitor see?">Public pages may show publication status, symbol, signal type, timeframe and educational context. Protected entry, stop-loss and targets are not shown on the homepage.</FaqItem><FaqItem number="03" question="How do member signals work?">A valid member session and verified access state are required before protected signal detail is requested.</FaqItem><FaqItem number="04" question="How are results presented?">Only evidence-backed public records that pass privacy and publication controls are shown.</FaqItem><FaqItem number="05" question="What are the risks?">Gold and leveraged markets can move quickly. Past results do not predict future outcomes, and no signal guarantees a result.</FaqItem></div></section>
  </div>;
}

function formatUpdateTime(value: string | undefined) {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat("en", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}
