import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div><strong>AI Market Analytics Pro</strong><p>Risk-aware market research, education and XAUUSD signal context.</p></div>
      <nav aria-label="Footer navigation">
        <Link href="/page/about">About</Link><Link href="/blog">Blog</Link>
        <Link href="/signals">Signals</Link><Link href="/page/contact">Contact</Link>
        <Link href="/page/privacy-policy">Privacy Policy</Link>
        <Link href="/page/terms-and-conditions">Terms</Link>
        <Link href="/page/risk-disclaimer">Risk Disclaimer</Link>
      </nav>
      <small>© {new Date().getFullYear()} AI Market Analytics Pro. All rights reserved.</small>
    </footer>
  );
}
