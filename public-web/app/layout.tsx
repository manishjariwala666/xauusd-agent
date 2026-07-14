import type { Metadata } from "next";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "https://venusrealm.net"),
  title: { default: "VenusRealm | Gold Market Intelligence", template: "%s | VenusRealm" },
  description: "Risk-first XAUUSD signals, gold market analysis, financial astrology and AI-assisted trading education.",
  applicationName: "VenusRealm"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><div className="shell"><SiteHeader /><main>{children}</main><SiteFooter /></div></body></html>;
}
