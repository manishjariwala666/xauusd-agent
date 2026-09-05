import { cookies } from "next/headers";
import Link from "next/link";
import { Icon } from "./icon";
import { MobileNav } from "./mobile-nav";
import { configuredLinks, primaryNavigation } from "@/lib/site-config";
import { ThemeSwitcher } from "./theme-switcher";

const MEMBER_SESSION_COOKIE = "vr_member_session";

export async function SiteHeader() {
  const links = configuredLinks();
  const cookieStore = await cookies();
  const hasMemberSession = Boolean(cookieStore.get(MEMBER_SESSION_COOKIE)?.value);
  const navigation = hasMemberSession
    ? primaryNavigation
    : primaryNavigation.filter((item) => item.href !== "/signals");

  return (
    <header className="site-header">
      <Link className="brand" href="/" aria-label="VenusRealm home"><span className="brand-mark"><Icon name="gold" size={22} /></span><span>Venus<span>Realm</span></span></Link>
      <nav className="desktop-nav" aria-label="Primary navigation">{navigation.map((item) => <Link href={item.href} key={item.href}>{item.label}</Link>)}</nav>
      <div className="header-actions">
        <ThemeSwitcher />
        <Link className="account-link" href={hasMemberSession ? "/signals" : "/login"}>
          <Icon name="shield" size={16} />
          {hasMemberSession ? "Member Desk" : "Member Access"}
        </Link>
        {links.telegram && <a className="button button-gold button-small" href={links.telegram} rel="noreferrer" target="_blank"><Icon name="send" size={17} />Join Telegram</a>}
      </div>
      <MobileNav items={navigation} loginUrl={hasMemberSession ? "/signals" : "/login"} telegramUrl={links.telegram} />
    </header>
  );
}
