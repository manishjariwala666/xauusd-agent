import Image from "next/image";
import {
  astrologyHighlights,
  upcomingAmavasya,
} from "@/lib/astrology-data";

export const metadata = {
  title: "Amavasya, Tithi & Nakshatra | VenusRealm Astrology",
  description:
    "Explore the upcoming Amavasya, Krishna Paksha Tithi, Purva Phalguni Nakshatra and the role of lunar timing in VenusRealm market research.",
};

export default function AstrologyPage() {
  return (
    <main className="content-page">

      <section className="astrology-hero">
        <div className="astrology-hero-copy">
          <span className="eyebrow">FINANCIAL ASTROLOGY</span>

          <h1>Upcoming Amavasya, Tithi & Nakshatra</h1>

          <p>
            VenusRealm studies lunar and planetary timing as an additional
            observational layer alongside price action, market structure,
            macroeconomic conditions and disciplined risk management.
            The upcoming Bhadrapada Amavasya provides a useful reference point
            for observing how a new lunar cycle begins and how market behaviour
            develops around that timing.
          </p>

          <div className="astrology-meta">
            <div>
              <span className="meta-label">Upcoming Amavasya</span>
              <strong>{upcomingAmavasya.name}</strong>
            </div>

            <div>
              <span className="meta-label">Date</span>
              <strong>{upcomingAmavasya.displayDate}</strong>
            </div>
          </div>
        </div>

        <div className="astrology-hero-visual">
          <Image
            src="/images/astrology/amavasya-hero.webp"
            alt="Amavasya new moon night with lunar timing information"
            width={1536}
            height={1024}
            priority
            className="astrology-hero-image"
          />
        </div>
      </section>


      <section className="astrology-section">
        <span className="eyebrow">UPCOMING LUNAR EVENT</span>
        <h2>{upcomingAmavasya.name}</h2>

        <p>
          Amavasya is the new-moon phase of the traditional Hindu lunar
          calendar and marks the completion of Krishna Paksha. During this
          phase the illuminated portion of the Moon visible from Earth becomes
          minimal, creating the transition point between one lunar cycle and
          the next.
        </p>

        <p>
          The upcoming Bhadrapada Amavasya is observed on
          {" "}{upcomingAmavasya.displayDate}. The reference Tithi begins on
          {" "}{upcomingAmavasya.startIst} and ends on
          {" "}{upcomingAmavasya.endIst}. Local Panchang timings can vary
          slightly according to geographic location, sunrise calculations and
          the system used by a particular calendar.
        </p>

        <p>
          VenusRealm presents this information as educational timing context.
          We do not treat a new moon, full moon, Nakshatra or planetary
          configuration as independent proof that Gold, Bitcoin or another
          financial market must move in a particular direction.
        </p>
      </section>


      <section className="astrology-section">
        <h2>Upcoming Panchang Highlights</h2>

        <div className="astrology-info-grid">
          {astrologyHighlights.map((item) => (
            <article key={item.id} className="astrology-info-card">
              <span className="card-kicker">{item.title}</span>
              <div className="card-label">{item.label}</div>
              <h3>{item.value}</h3>
              {item.note ? <p>{item.note}</p> : null}
            </article>
          ))}
        </div>
      </section>


      <section className="astrology-section">
        <div className="astrology-notice-card">
          <span className="eyebrow">TITHI</span>
          <h2>Krishna Amavasya</h2>

          <p>
            Tithi is a lunar-day measurement based on the changing angular
            relationship between the Sun and Moon. Each lunar month is divided
            into thirty Tithis, with fifteen belonging to the waxing phase and
            fifteen to the waning phase.
          </p>

          <p>
            Krishna Amavasya is the final Tithi of the waning half of the lunar
            month. It represents the point immediately before the next waxing
            cycle begins. In traditional calendars Amavasya carries religious,
            cultural and observational significance, but in VenusRealm market
            research it is treated primarily as a time marker.
          </p>

          <p>
            When studying market behaviour around a Tithi, the correct method
            is not to assume a predetermined bullish or bearish outcome.
            Instead, researchers can compare volatility, direction, liquidity,
            session structure and important macro events occurring around the
            same period.
          </p>
        </div>
      </section>


      <section className="astrology-section">
        <div className="astrology-notice-card">
          <span className="eyebrow">NAKSHATRA</span>
          <h2>Purva Phalguni</h2>

          <p>
            The reference Nakshatra for this upcoming Amavasya is
            {" "}Purva Phalguni. Nakshatras divide the Moon&apos;s path through
            the zodiac into twenty-seven traditional lunar sectors. Because
            the Moon moves quickly, the active Nakshatra changes approximately
            once each day.
          </p>

          <p>
            For VenusRealm, Nakshatra information can become one component of
            a broader timing database. Historical observations may later be
            compared with XAUUSD volatility, intraday session behaviour,
            momentum conditions and reversal frequency.
          </p>

          <p>
            The important distinction is that correlation does not establish
            causation. If a particular market reaction happened during Purva
            Phalguni in the past, it does not mean the same reaction must occur
            during the next occurrence.
          </p>
        </div>
      </section>


      <section className="astrology-section">
        <div className="astrology-notice-card">
          <span className="eyebrow">MARKET OBSERVATION</span>
          <h2>How VenusRealm Uses Astrology</h2>

          <p>
            VenusRealm&apos;s financial-astrology research is designed as a
            supplementary timing framework rather than a standalone trading
            system. Any lunar or planetary observation should first be tested
            against real market data.
          </p>

          <p>
            For Gold analysis, that means examining price structure, liquidity
            zones, trend direction, support and resistance, volatility,
            economic releases and broader macroeconomic conditions. Astrology
            can be recorded as an additional timestamp or contextual factor,
            but it should never override observable market risk.
          </p>

          <p>
            This separation is especially important during major events such
            as central-bank decisions, inflation data, employment releases,
            geopolitical shocks or sudden liquidity changes. A strong
            fundamental catalyst can dominate price behaviour regardless of
            the lunar calendar.
          </p>
        </div>
      </section>


      <section className="astrology-section">
        <div className="astrology-notice-card">
          <span className="eyebrow">RESEARCH PRINCIPLE</span>
          <h2>Never a Standalone Signal</h2>

          <p>
            Amavasya, Tithi, Nakshatra and planetary cycles should never be
            interpreted as automatic BUY or SELL signals. VenusRealm separates
            timing observations from actionable trading decisions so that
            research remains measurable and risk-aware.
          </p>

          <p>
            Future astrology updates can compare lunar events with historical
            XAUUSD performance, volatility expansion, session behaviour and
            technical structure. Only patterns that survive objective testing
            should be considered meaningful enough for further study.
          </p>

          <p>
            Every trading decision involves uncertainty. Astrology does not
            remove that uncertainty, and it does not eliminate the possibility
            of loss. Independent price verification, risk limits and proper
            position management remain essential.
          </p>
        </div>
      </section>


      <section className="astrology-section">
        <div className="astrology-notice-card">
          <span className="eyebrow">LUNAR CYCLE RESEARCH</span>
          <h2>What We Will Track Around Amavasya</h2>

          <p>
            VenusRealm will gradually build a historical record around major
            lunar events rather than relying on isolated observations. The
            research can compare Amavasya dates with XAUUSD volatility,
            directional momentum, London and New York session behaviour,
            intraday range expansion and important reversal zones.
          </p>

          <p>
            The purpose is to identify whether any repeatable statistical
            relationship exists. Observations that do not survive historical
            comparison should not influence trading decisions. This keeps the
            astrology section educational, measurable and separate from the
            platform&apos;s technical, macroeconomic and risk-management
            frameworks.
          </p>
        </div>
      </section>

    </main>
  );
}
