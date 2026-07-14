"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const primary = [
  ["Dashboard", "/admin/dashboard", "⌂"], ["Blog Studio", "/admin/posts", "▤"],
  ["Pages", "/admin/pages", "□"], ["Categories", "/admin/categories", "◇"],
  ["Media", "/admin/media", "▧"], ["SEO", "/admin/seo", "⌁"],
  ["Signals", "/admin/signals", "↗"], ["Announcements", "/admin/announcements", "◉"],
  ["Verified Results", "/admin/results", "✓"]
] as const;
const future = [["Social", "◎"], ["Agents", "✣"], ["Logs", "≡"], ["Settings", "⚙"]] as const;

export function AdminNavigation() {
  const pathname = usePathname();
  return <nav className="sidebar-nav">
    <div className="nav-label">Workspace</div>
    {primary.map(([label, href, icon]) => <Link className={`nav-item ${pathname.startsWith(href) ? "active" : ""}`} href={href} key={href}><span><i aria-hidden="true">{icon}</i>{label}</span></Link>)}
    <div className="nav-label">Tools</div>
    {future.map(([label, icon]) => <span aria-disabled="true" className="nav-item disabled" key={label}><span><i aria-hidden="true">{icon}</i>{label}</span><small>Coming later</small></span>)}
  </nav>;
}

export function AdminBreadcrumbs() {
  const pathname = usePathname();
  const parts = pathname.split("/").filter(Boolean).slice(1);
  const labels = parts.map((part, index) => index === 1 && parts[0] === "posts" && part !== "new" ? `Post #${part}` : part === "edit" ? "Edit" : part.replaceAll("-", " "));
  return <div className="breadcrumbs" aria-label="Breadcrumb"><Link href="/admin/dashboard">Admin</Link>{labels.map((label, index) => <span key={`${label}-${index}`}><b aria-hidden="true">/</b><span>{label}</span></span>)}</div>;
}

export function AdminMenuButton() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    document.documentElement.classList.toggle("admin-menu-open", open);
    return () => document.documentElement.classList.remove("admin-menu-open");
  }, [open]);
  return <button className="menu-button" aria-label="Toggle navigation" aria-expanded={open} onClick={() => setOpen(value => !value)}>☰</button>;
}
