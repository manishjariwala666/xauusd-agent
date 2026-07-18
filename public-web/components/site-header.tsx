import Link from "next/link";
import { Icon } from "./icon";
import { MobileNav } from "./mobile-nav";
import { configuredLinks, primaryNavigation } from "@/lib/site-config";
import { ThemeSwitcher } from "./theme-switcher";

export function SiteHeader() {
  const links = configuredLinks();
  return (
    <header className="site-header">
      <Link className="brand" href="/" aria-label="VenusRealm home"><span className="brand-mark"><Icon name="gold" size={22} /></span><span>Venus<span>Realm</span></span></Link>
      <nav className="desktop-nav" aria-label="Primary navigation">{primaryNavigation.map((item) => <Link href={item.href} key={item.href}>{item.label}</Link>)}</nav>
      <div className="header-actions"><ThemeSwitcher /><Link className="login-link" href="/login">Login</Link>{links.telegram && <a className="button button-gold button-small" href={links.telegram} rel="noreferrer" target="_blank"><Icon name="send" size={17} />Join Telegram</a>}</div>
      <MobileNav items={primaryNavigation} loginUrl="/login" telegramUrl={links.telegram} />
    </header>
  );
}
