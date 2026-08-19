import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "VenusRealm Admin", template: "%s | VenusRealm Admin" },
  description: "Secure administration for AI Market Analytics Pro.",
  robots: { index: false, follow: false, noarchive: true }
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
