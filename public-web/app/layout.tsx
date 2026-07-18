import type { Metadata, Viewport } from "next";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "https://venusrealm.net"),
  title: { default: "VenusRealm | Gold Market Intelligence", template: "%s | VenusRealm" },
  description: "Risk-first XAUUSD signals, gold market analysis, financial astrology and AI-assisted trading education.",
  applicationName: "VenusRealm"
};
export const viewport: Viewport = { colorScheme: "light dark", themeColor: [{ media: "(prefers-color-scheme: light)", color: "#ffffff" }, { media: "(prefers-color-scheme: dark)", color: "#0a1729" }] };

const themeInit = `(function(){try{var p=localStorage.getItem('vr-theme')||'auto';var d=p==='dark'||(p==='auto'&&matchMedia('(prefers-color-scheme: dark)').matches);var e=document.documentElement;e.dataset.theme=d?'dark':'light';e.dataset.themePreference=p;e.style.colorScheme=d?'dark':'light'}catch(e){}})()`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{ __html: themeInit }} /></head><body><div className="shell"><SiteHeader /><main>{children}</main><SiteFooter /></div></body></html>;
}
