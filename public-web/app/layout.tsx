import type { Metadata } from "next";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "https://venusrealm.net"),
  title: { default: "AI Market Analytics Pro", template: "%s | AI Market Analytics Pro" },
  description: "Risk-aware XAUUSD signals, market analysis and trading education."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><div className="shell"><SiteHeader /><main>{children}</main><SiteFooter /></div></body></html>;
}
