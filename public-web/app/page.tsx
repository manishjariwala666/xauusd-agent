import Image from "next/image";
import Link from "next/link";
import { ContentGrid } from "@/components/content-grid";
import { FaqItem, ProcessStep, ResearchToolCard, SnapshotItem } from "@/components/homepage-sections";
import { Icon, type IconName } from "@/components/icon";
import { getContent, getResultSnapshot, getSignalSnapshot } from "@/lib/api";
import { configuredLinks } from "@/lib/site-config";
import "./home-premium.css";
import "./home-visual-upgrade.css";

export const revalidate = 300;

const tools: { icon: IconName; title: string; text: string; href: string }[] = [
  { icon: "gold", title: "Gold signals", text: "Structured XAUUSD levels with entries, invalidation and clear risk context.", href: "/signals" },
  { icon: "chart", title: "Market analysis", text: "Technical and macro research built for considered decisions—not reaction.", href: "/category/analysis-department" },
  { icon: "moon", title: "Financial astrology", text: "Educational exploration of planetary cycles and market timing.", href: "/astrology" },
  { icon: "book", title: "Learning", text: "Practical market education grounded in discipline and risk control.", href: "/category/market-education" },
  { icon: "send", title: "Telegram alerts", text: "Fast channel delivery when a verified public alert is available.", href: "/contact" },
  { icon: "brain", title: "AI research", text: "AI-assisted synthesis with explicit risk framing and editorial review.", href: "/blog" },
];

function formatUpdateTime(value: unknown) {
  if (!value) return "Not available";
  try {
    return new Intl.DateTimeFormat("en", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(String(value)));
  } catch {
    return "Not available";
  }
}

export default async function HomePage() {
  const [content, signals, results] = await Promise.all([
    getContent(undefined, 12),
    getSignalSnapshot(),
    getResultSnapshot(),
  ]);

  const publishedBlogs = content
    .filter((item) => ["BLOG", "AI_BLOG", "ANALYSIS", "EDUCATION", "ADVISORY"].includes(item.content_type))
    .slice(0, 6);
  const astrology = content.filter((item) => `${item.title} ${item.excerpt || ""} ${item.category_title || ""}`.toLowerCase().includes("astrolog"));
  const latest = publishedBlogs[0];
  const signal = signals[0];
  const links = configuredLinks();
  const updateTime = signal?.updated_at || signal?.published_at || signal?.signal_time || latest?.published_at || latest?.created_at;
  const researchTools = tools.map((tool) => tool.title === "Telegram alerts" ? { ...tool, href: links.telegram || "/contact" } : tool);

  return <div className="home-page">
    <section className="home-hero home-hero-visualized">
      <Image className="home-hero-art" src="/visuals/gold-market-banner.svg" alt="Abstract XAUUSD market intelligence visualization" fill priority sizes="(max-width: 700px) 100vw, 1240px" />
      <div className="home-hero-overlay" />
      <div className="home-hero-copy">
        <span className="eyebrow"><span />GOLD INTELLIGENCE, BUILT FOR CLARITY</span>
        <h1>Read the gold market with <em>calm conviction.</em></h1>
        <p>VenusRealm brings XAUUSD signals, market structure, financial astrology and AI-assisted research into one disciplined, educational view.</p>
        <div className="home-hero-actions">
          <Link className="button button-gold" href="/signals">View Gold Signals <Icon name="arrow" size={18} /></Link>
          {links.telegram && <a className="button button-ghost" href={links.telegram} rel="noreferrer" target="_blank"><Icon name="send" size={18} />Join Telegram</a>}
        </div>
        <div className="home-hero-meta"><span><Icon name="brain" size={15} />AI-assisted research</span><span><Icon name="shield" size={15} />Risk-first analysis</span><span><Icon name="book" size={15} />Educational content</span></div>
      </div>
      <div className="home-market-card" aria-label="VenusRealm XAUUSD research panel">
        <div className="home-market-card-head"><span>VENUSREALM / GOLD DESK</span><span className="home-live-dot">Research layer</span></div>
        <div className="home-market-quote"><small>Current public state</small><strong>{signal?.signal_type || "WATCH"}</strong><span>{signal?.symbol || "XAUUSD"}</span></div>
        <div className="home-market-stats"><div><span>Timeframe</span><b>{signal?.timeframe || "Research"}</b></div><div><span>Latest update</span><b>{formatUpdateTime(updateTime)}</b></div></div>
        <Link className="text-link" href="/signals">Open signal desk <Icon name="arrow" size={16}/></Link>
      </div>
    </section>

    <section className="home-section home-desk" aria-labelledby="snapshot-title">
      <div className="home-desk-head"><div><span className="eyebrow">MARKET SNAPSHOT</span><h2 id="snapshot-title">The desk, at a glance.</h2></div><span className="data-note"><span className="status-dot" />Cached public data</span></div>
      <div className="home-snapshot-grid">
        <SnapshotItem label="XAUUSD status" value={signal?.signal_type || "No verified signal"} detail={signal?.symbol || "Awaiting a published market row"} />
        <SnapshotItem label="Latest published signal" value={signal?.price != null ? String(signal.price) : "Not available"} detail={signal ? "Open the desk for risk levels" : "No public signal is active"} />
        <SnapshotItem label="Latest analysis" value={latest?.title || "Research unavailable"} detail={latest?.category_title || "Published editorial research"} href={latest ? `/blog/${latest.slug}` : "/blog"} />
        <SnapshotItem label="Last public update" value={formatUpdateTime(updateTime)} detail="Published public data" />
      </div>
    </section>

    <section className="home-section" aria-labelledby="tools-title">
      <div className="home-heading"><div><span className="eyebrow">WHAT VENUSREALM OFFERS</span><h2 id="tools-title">One research layer. Six focused tools.</h2></div><p>Built to help readers separate market context from market noise.</p></div>
      <div className="home-tools">{researchTools.map((tool) => <ResearchToolCard key={tool.title} {...tool} />)}</div>
    </section>

    <section className="home-section home-dark-band" aria-labelledby="signals-title">
      <div className="home-heading"><div><span className="eyebrow">LATEST GOLD SIGNALS</span><h2 id="signals-title">Defined levels. Visible risk.</h2></div><Link className="text-link" href="/signals">Open signal desk <Icon name="arrow" size={16} /></Link></div>
      {signals.length ? <div className="home-signal-grid">{signals.slice(0, 3).map((item, index) => <article className="home-signal-card" key={item.id || index}><header><span>{item.symbol || "XAUUSD"}</span><b>{item.signal_type || "WATCH"}</b></header><dl><div><dt>Timeframe</dt><dd>{item.timeframe || "—"}</dd></div><div><dt>Entry</dt><dd>{item.price ?? "—"}</dd></div><div><dt>Stop loss</dt><dd>{item.stop_loss ?? "—"}</dd></div><div><dt>Targets</dt><dd>{[item.target_1, item.target_2, item.target_3].filter((value) => value != null).join(" · ") || "—"}</dd></div></dl></article>)}</div> : <div className="empty-state empty-dark"><Icon name="clock" /><div><h3>No verified signal is currently published</h3><p>The desk will display real levels here when a public signal is available. No placeholder prices are shown.</p></div></div>}
    </section>

    <section className="home-section" aria-labelledby="analysis-title">
      <div className="home-heading"><div><span className="eyebrow">LATEST MARKET ANALYSIS</span><h2 id="analysis-title">Research for the next considered move.</h2></div><Link className="text-link" href="/blog">Browse all research <Icon name="arrow" size={16} /></Link></div>
      <ContentGrid items={publishedBlogs} />
    </section>

    <section className="home-section home-lens" aria-labelledby="astrology-title">
      <div className="home-lens-visual" aria-hidden="true"><Image src="/visuals/gold-market-banner.svg" alt="" fill sizes="(max-width: 700px) 100vw, 55vw" /></div>
      <div className="home-lens-copy"><span className="eyebrow">FINANCIAL ASTROLOGY</span><h2 id="astrology-title">A wider lens on market timing.</h2><p>VenusRealm treats astrology as an educational timing framework—not a standalone trading signal. Planetary cycles are considered alongside market data, structure and risk.</p><Link className="button button-light" href="/astrology">Explore the methodology <Icon name="arrow" size={18} /></Link></div>
      <div className="home-lens-card"><Icon name="moon" size={32} /><span>Planetary market timing</span><strong>{astrology.length ? `${astrology.length} published insight${astrology.length === 1 ? "" : "s"}` : "Upcoming research desk"}</strong><p>{astrology.length ? astrology[0].title : "No astrology article has been published yet. New material will appear only after editorial review."}</p></div>
    </section>

    <section className="home-section" id="how-it-works" aria-labelledby="process-title">
      <div className="home-heading"><div><span className="eyebrow">HOW IT WORKS</span><h2 id="process-title">From market input to public insight.</h2></div></div>
      <ol className="home-process"><ProcessStep number="01" icon="globe" title="Market data" text="Published market inputs and price context form the factual base."/><ProcessStep number="02" icon="brain" title="AI + astrology analysis" text="Research tools synthesize structure, narrative and timing frameworks."/><ProcessStep number="03" icon="shield" title="Risk and compliance review" text="Claims, levels and language are checked through a risk-first lens."/><ProcessStep number="04" icon="send" title="Publish and alert" text="Approved public content is released to the site and configured channels."/></ol>
    </section>

    <section className="home-section home-discipline" aria-labelledby="why-title">
      <div><span className="eyebrow">WHY VENUSREALM</span><h2 id="why-title">Designed for disciplined readers, not impulsive clicks.</h2><p>Every section prioritizes context, explicit uncertainty and educational value.</p></div>
      <div className="home-principles">{["Risk-first approach","Transparent educational analysis","Fast configured alerts","Multi-channel updates","Structured editorial content","Human approval where applicable"].map((item) => <span key={item}><Icon name="check" size={17} />{item}</span>)}</div>
    </section>

    <section className="home-section home-proof" id="results" aria-labelledby="results-title">
      <div><span className="eyebrow">VERIFIED RESULTS</span><h2 id="results-title">Proof should be documented, not promised.</h2><p>Only evidence-backed, redacted, compliance-approved records are eligible. Account profit, ROI and unverified percentages are never inferred.</p><Link className="text-link" href="/results">Read methodology and records <Icon name="arrow" size={16}/></Link></div>
      {results.length ? <div className="home-proof-card"><Icon name="target" size={28}/><strong>{results[0].symbol} {results[0].direction}: {results[0].result_points} {results[0].result_unit}</strong><span>{results[0].public_summary}</span></div> : <div className="home-proof-card"><Icon name="target" size={28}/><strong>Awaiting verified public records</strong><span>No synthetic claims or placeholder percentages are shown.</span></div>}
    </section>

    <section className="home-section home-video" aria-labelledby="video-title">
      <div><span className="eyebrow">VIDEO & YOUTUBE</span><h2 id="video-title">Watch the research process.</h2><p>{links.video || links.youtube ? "Open the configured VenusRealm video channel for published market education." : "No public video channel is configured for this preview. No placeholder videos are loaded."}</p></div>
      {(links.video || links.youtube) && <a className="button button-dark" href={links.video || links.youtube} rel="noreferrer" target="_blank">Open YouTube <Icon name="arrow" size={18} /></a>}
    </section>

    <section className="home-section home-faq" id="faq" aria-labelledby="faq-title">
      <div className="home-heading"><div><span className="eyebrow">FAQ</span><h2 id="faq-title">Clear answers before you begin.</h2></div></div>
      <div><FaqItem question="Are signals financial advice?">No. Signals and analysis are educational information and do not account for your circumstances. You remain responsible for every financial decision.</FaqItem><FaqItem question="How are signals created?">Public signals may combine market data, structured analysis and automated research, followed by the approval controls applicable to the publishing workflow.</FaqItem><FaqItem question="Is astrology used alone?">No. Astrology is presented as an educational timing lens and should never replace market structure, risk management or independent judgment.</FaqItem><FaqItem question="Where are alerts delivered?">Alerts appear on the public signal desk. Telegram or WhatsApp links are shown only when those public channels are configured.</FaqItem><FaqItem question="What are the risks?">Gold and leveraged markets can move quickly. Losses may exceed expectations, past results do not predict future outcomes, and no signal guarantees a result.</FaqItem></div>
    </section>

    <section className="home-section home-final">
      <div><span className="eyebrow">READ THE MARKET DIFFERENTLY</span><h2>Clarity for gold. Discipline for every decision.</h2></div>
      <div className="home-hero-actions"><Link className="button button-gold" href="/signals">View Signals</Link>{links.telegram && <a className="button button-light" href={links.telegram} rel="noreferrer" target="_blank">Join Telegram</a>}<Link className="button button-ghost" href="/blog">Read Latest Analysis</Link></div>
    </section>
  </div>;
}
