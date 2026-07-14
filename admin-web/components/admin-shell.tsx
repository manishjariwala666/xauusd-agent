import Link from "next/link";
import type { ReactNode } from "react";
import type { AdminUser } from "@/lib/admin-api";
import { LogoutButton } from "./logout-button";
import { AdminBreadcrumbs, AdminMenuButton, AdminNavigation } from "./admin-navigation";

export function AdminShell({ user, children }: { user: AdminUser; children: ReactNode }) {
  const initials = user.email.slice(0, 2).toUpperCase();
  return <div className="admin-shell">
    <aside className="sidebar" aria-label="Admin navigation">
      <Link className="admin-brand" href="/admin/dashboard"><span className="brand-mark">VR</span><span><strong>VenusRealm</strong><small>ADMIN CMS</small></span></Link>
      <section className="admin-profile"><span className="avatar">{initials}</span><div><strong>{user.email.split("@")[0]}</strong><small>{user.role}ISTRATOR</small></div></section>
      <AdminNavigation />
      <aside className="risk-note"><strong>Risk notice</strong><p>Trading content is informational and not financial advice.</p></aside>
      <LogoutButton />
    </aside>
    <div className="admin-content">
      <header className="topbar">
        <div className="topbar-start"><AdminMenuButton /><form className="global-search" action="/admin/posts"><label><span aria-hidden="true">⌕</span><input name="search" placeholder="Search content…" aria-label="Search content" /></label></form></div>
        <div className="topbar-end"><button className="notification-button" aria-label="Notifications — coming later" disabled>♢</button><span className="top-avatar">{initials}</span><div className="top-user"><strong>{user.email.split("@")[0]}</strong><small>{user.role}</small></div></div>
      </header>
      <AdminBreadcrumbs />
      <main className="admin-main">{children}</main>
    </div>
  </div>;
}
