import Link from "next/link";
import { Icon } from "./icon";
import { configuredLinks, configuredSocialLinks } from "@/lib/site-config";

export function SiteFooter() {
  const social = configuredSocialLinks();
  const links = configuredLinks();
  const resources: [string, string][] = [["Blog","/blog"],["Astrology","/astrology"],["Learning","/category/market-education"],["FAQ","/#faq"]];
  if (links.youtube) resources.splice(3, 0, ["YouTube", links.youtube]);
  return (
    <footer className="site-footer">
      <div className="footer-lead"><Link className="brand footer-brand" href="/"><span className="brand-mark"><Icon name="gold" size={22} /></span><span>Venus<span>Realm</span></span></Link><p>Risk-first gold market intelligence, educational analysis and carefully structured public research.</p></div>
      <div className="footer-columns">
        <FooterColumn title="VenusRealm" links={[["About","/about"],["Automation Services","/automation-services"],["Contact","/contact"],["How It Works","/#how-it-works"]]} />
        <FooterColumn title="Markets" links={[["Gold Signals","/signals"],["Market Analysis","/category/analysis-department"],["Verified Results","/results"],["Announcements","/announcements"]]} />
        <FooterColumn title="Resources" links={resources} />
        <FooterColumn title="Legal" links={[["Risk Disclaimer","/legal/risk-disclaimer"],["Privacy Policy","/legal/privacy-policy"],["Terms and Conditions","/legal/terms"],["Cookie Policy","/legal/cookie-policy"],["Refund Policy","/legal/refund-policy"]]} />
        {social.length > 0 && <div className="footer-column"><h2>Connect</h2>{social.map((item) => <a href={item.href} key={item.label} rel="noreferrer" target="_blank">{item.label}</a>)}</div>}
      </div>
      <div className="footer-risk"><Icon name="shield" /><p><strong>Global risk disclaimer:</strong> Market analysis and signals are educational information, not financial advice. Trading leveraged products can result in substantial loss. Never risk capital you cannot afford to lose.</p></div>
      <div className="footer-bottom"><small>© {new Date().getFullYear()} VenusRealm. All rights reserved.</small><small>Research before reaction. Risk before reward.</small></div>
    </footer>
  );
}

function FooterColumn({ title, links }: { title: string; links: [string, string][] }) {
  return <div className="footer-column"><h2>{title}</h2>{links.map(([label, href]) => <Link href={href} key={href}>{label}</Link>)}</div>;
}
