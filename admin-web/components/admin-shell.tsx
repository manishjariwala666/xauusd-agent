import Link from "next/link";
import type { ReactNode } from "react";
import type { AdminUser } from "@/lib/admin-api";
import { LogoutButton } from "./logout-button";

const futureSections = ["Media", "Signals", "Agents", "Users", "Analytics", "Settings"];

export function AdminShell({ user, children }: { user: AdminUser; children: ReactNode }) {
  return (
    <div className="admin-shell">
      <aside className="sidebar" aria-label="Admin navigation">
        <Link className="admin-brand" href="/admin/dashboard">VenusRealm <span>Admin</span></Link>
        <nav>
          <Link className="nav-item active" href="/admin/dashboard">Dashboard</Link>
          <Link className="nav-item" href="/admin/posts">Posts</Link>
          <Link className="nav-item" href="/admin/pages">Pages</Link>
          <Link className="nav-item" href="/admin/categories">Categories</Link>
          <div className="nav-label">Future phases</div>
          {futureSections.map((label) => <span aria-disabled="true" className="nav-item disabled" key={label}>{label}<small>Later</small></span>)}
        </nav>
        <div className="sidebar-note">Local Phase 2A CMS. Production actions remain disabled.</div>
      </aside>
      <div className="admin-content">
        <header className="topbar">
          <div><small>ADMIN CONTROL ROOM</small><strong>AI Market Analytics Pro</strong></div>
          <div className="user-menu"><span>{user.email}</span><LogoutButton /></div>
        </header>
        <div className="breadcrumbs" aria-label="Breadcrumb"><Link href="/admin">Admin</Link><span>/</span><span>Dashboard</span></div>
        <main className="admin-main">{children}</main>
      </div>
    </div>
  );
}
