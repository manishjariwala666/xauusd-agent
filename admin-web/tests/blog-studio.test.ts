import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const root = resolve(import.meta.dirname, "..");
const source = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("Phase 2B Blog Studio", () => {
  it("renders factual KPIs and a body-free server-paginated posts table", () => {
    const list = source("components/content-list.tsx");
    const api = source("lib/content-api.ts");
    for (const label of ["Total Posts", "Published", "Drafts", "Scheduled", "Trashed", "Total Views"]) expect(list).toContain(label);
    for (const column of ["Category", "Status", "Views", "SEO", "Slug", "Author", "Updated", "Actions"]) expect(list).toContain(column);
    expect(api.match(/type ContentSummary[\s\S]*?};/)?.[0]).not.toContain("body:");
    expect(list).toContain("pageHref");
  });

  it("offers only real post actions through the protected content BFF", () => {
    const actions = source("components/content-actions.tsx") + source("components/content-editor.tsx");
    const proxy = source("app/api/admin/content/[...path]/route.ts");
    for (const action of ["publish", "unpublish", "duplicate", "trash"]) expect(actions).toContain(action);
    expect(actions).toContain("X-CSRF-Token");
    expect(proxy).toContain("duplicate");
    expect(actions).not.toMatch(/onClick=\{\(\) => \{\}\}/);
  });

  it("provides editor preview, SEO, social, schema and metadata panels", () => {
    const editor = source("components/content-editor.tsx") + source("components/seo-workbench.tsx");
    for (const tab of ["Post Preview", "SEO Settings", "Open Graph", "X / Twitter", "FAQ / Schema", "Content Metadata"]) expect(editor).toContain(tab);
    expect(editor).toContain("Save SEO");
    expect(editor).toContain("Collapsed for performance");
    expect(editor).toContain("All changes saved");
  });

  it("sanitizes previews without dangerous HTML injection", () => {
    const preview = source("components/safe-content-preview.tsx");
    expect(preview).toContain("<script");
    expect(preview).toContain("<h1");
    expect(preview).toContain("<h2");
    expect(preview).toContain("<h3");
    expect(preview).toContain("<blockquote");
    expect(preview).not.toContain("dangerouslySetInnerHTML");
  });
});
