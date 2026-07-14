"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Icon } from "./icon";
import type { NavigationItem } from "@/lib/site-config";

export function MobileNav({ items, loginUrl, telegramUrl }: { items: NavigationItem[]; loginUrl: string; telegramUrl?: string }) {
  const pathname = usePathname();
  return <MobileNavMenu key={pathname} items={items} loginUrl={loginUrl} telegramUrl={telegramUrl} />;
}

function MobileNavMenu({ items, loginUrl, telegramUrl }: { items: NavigationItem[]; loginUrl: string; telegramUrl?: string }) {
  const [open, setOpen] = useState(false);
  return <div className="mobile-navigation">
    <button className="menu-toggle" type="button" aria-expanded={open} aria-controls="mobile-menu" aria-label={open ? "Close navigation" : "Open navigation"} onClick={() => setOpen((value) => !value)}><Icon name={open ? "x" : "menu"} /></button>
    {open && <div className="mobile-menu" id="mobile-menu"><nav aria-label="Mobile navigation">{items.map((item) => <Link href={item.href} key={item.href}>{item.label}</Link>)}</nav><div className="mobile-actions"><a href={loginUrl}>Login</a>{telegramUrl && <a className="button button-gold" href={telegramUrl} rel="noreferrer" target="_blank">Join Telegram</a>}</div></div>}
  </div>;
}
