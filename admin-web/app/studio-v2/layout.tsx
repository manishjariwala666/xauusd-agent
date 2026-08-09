import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import type { ReactNode } from "react";

import { fetchAdminSession } from "@/lib/admin-api";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

export default async function StudioV2Layout({
  children,
}: {
  children: ReactNode;
}) {
  const token =
    (await cookies()).get(ADMIN_SESSION_COOKIE)?.value || "";

  const result = await fetchAdminSession(token);

  if (result.status === "forbidden") {
    redirect("/admin/forbidden");
  }

  if (result.status !== "authenticated" || !result.user) {
    redirect("/admin/login");
  }

  const deploymentContext = String(process.env.CONTEXT || "")
    .trim()
    .toLowerCase();
  const environmentLabel =
    deploymentContext === "production"
      ? "Production"
      : deploymentContext === "deploy-preview" ||
          deploymentContext === "branch-deploy"
        ? "Preview staging"
        : process.env.NODE_ENV === "production"
          ? "Production"
          : "Local development";

  return (
    <div className="studio-v2-shell">
      <aside className="studio-v2-sidebar">
        <div className="studio-v2-brand">
          <span className="studio-v2-logo">VR</span>

          <div>
            <strong>VenusRealm</strong>
            <small>Custom CMS V2</small>
          </div>
        </div>

        <nav className="studio-v2-navigation">
          <span className="studio-v2-nav-label">CONTENT</span>

          <Link href="/studio-v2">Content Studio</Link>
          <Link href="/studio-v2/posts">Posts</Link>
          <Link href="/studio-v2/posts?status=draft">Drafts</Link>
          <Link href="/studio-v2/media">Media Library</Link>
          <Link href="/studio-v2/gallery">Gallery Manager</Link>
          <Link href="/studio-v2/seo">SEO Studio</Link>
          <Link href="/studio-v2/signals">Signals</Link>

          <span className="studio-v2-nav-label">INTELLIGENCE</span>

          <Link href="/studio-v2/ai">AI Tools</Link>
          <Link href="/studio-v2/master-ai">
            Master AI Console
          </Link>
          <Link href="/studio-v2/agents">Agents</Link>
          <Link href="/studio-v2/approvals">
            Approvals
          </Link>
        </nav>

        <div className="studio-v2-environment">
          <span>Environment</span>
          <strong>{environmentLabel}</strong>
          <small>No automatic publishing</small>
        </div>
      </aside>

      <section className="studio-v2-main">
        <header className="studio-v2-topbar">
          <div>
            <strong>VenusRealm Custom CMS</strong>
            <span>Independent V2 workspace</span>
          </div>

          <div className="studio-v2-topbar-actions">
            <span>Secure admin session</span>

            <Link href="/admin/dashboard">
              Legacy Admin
            </Link>
          </div>
        </header>

        <div className="studio-v2-content">
          {children}
        </div>
      </section>
    </div>
  );
}
