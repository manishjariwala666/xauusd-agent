import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="site-header">
      <Link className="brand" href="/">AI Market Analytics Pro<span>.</span></Link>
      <nav aria-label="Primary navigation">
        <Link href="/blog">Blog</Link>
        <Link href="/signals">Signals</Link>
        <Link href="/category/analysis-department">Market Analysis</Link>
        <Link href="/announcements">Announcements</Link>
      </nav>
      <a className="button small" href={process.env.ADMIN_DASHBOARD_URL || "https://admin.venusrealm.net"}>Sign In</a>
    </header>
  );
}
