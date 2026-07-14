import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const root = resolve(import.meta.dirname, "..");
const source = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("Phase 3B SEO management", () => {
  it("provides editable fields, previews, structured data and Media Library selection", () => {
    const editor = source("components/seo-workbench.tsx");
    for (const label of ["SEO title", "Meta description", "Focus keyword", "Secondary keywords", "Canonical URL", "Include in sitemap", "Open Graph", "X / Twitter", "Add FAQ", "Schema JSON-LD", "Save SEO", "Validate"]) expect(editor).toContain(label);
    expect(editor).toContain("/api/admin/media");
    expect(editor).toContain("include_structured=true");
    expect(editor).not.toContain("dangerouslySetInnerHTML");
  });

  it("protects writes in the BFF and exposes a paginated dashboard", () => {
    expect(existsSync(resolve(root, "app/admin/(protected)/seo/page.tsx"))).toBe(true);
    const proxy = source("app/api/admin/seo/[...path]/route.ts");
    const dashboard = source("components/seo-dashboard.tsx");
    expect(proxy).toContain("verifyCsrfToken");
    expect(proxy).toContain("ADMIN_SESSION_COOKIE");
    expect(proxy).toContain("X-Admin-BFF-Key");
    expect(dashboard).toContain("pageHref");
    expect(dashboard).toContain("Run validation");
    expect(dashboard).not.toMatch(/DATABASE_URL|service.role/i);
  });
});
