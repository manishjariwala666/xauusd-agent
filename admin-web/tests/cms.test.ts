import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const root = resolve(import.meta.dirname, "..");
const source = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("Phase 2A local CMS", () => {
  it("provides every approved posts, pages and categories route", () => {
    for (const route of [
      "app/admin/(protected)/posts/page.tsx",
      "app/admin/(protected)/posts/new/page.tsx",
      "app/admin/(protected)/posts/[id]/edit/page.tsx",
      "app/admin/(protected)/pages/page.tsx",
      "app/admin/(protected)/pages/new/page.tsx",
      "app/admin/(protected)/pages/[id]/edit/page.tsx",
      "app/admin/(protected)/categories/page.tsx"
    ]) expect(existsSync(resolve(root, route))).toBe(true);
  });

  it("routes mutations through the CSRF-protected BFF", () => {
    const proxy = source("app/api/admin/content/[...path]/route.ts");
    expect(proxy).toContain("verifyCsrfToken");
    expect(proxy).toContain("ADMIN_SESSION_COOKIE");
    expect(proxy).toContain("X-Admin-BFF-Key");
    expect(proxy).not.toContain("NEXT_PUBLIC");
  });

  it("uses lightweight editor features without rich-text dependencies", () => {
    const editor = source("components/content-editor.tsx");
    const pkg = source("package.json");
    expect(editor).toContain("beforeunload");
    expect(editor).toContain("word-count");
    expect(editor).toContain("<textarea");
    expect(pkg).not.toMatch(/tinymce|ckeditor|quill|tiptap/);
  });

  it("keeps public preview URLs server-configured", () => {
    const index = source("components/content-index-page.tsx");
    const list = source("components/content-list.tsx");
    expect(index).toContain("process.env.PUBLIC_WEBSITE_URL");
    expect(list).toContain("Open preview");
    expect(list).not.toContain("venusrealm.net");
  });

  it("keeps lists server-paginated and responsive", () => {
    const api = source("lib/content-api.ts");
    const css = source("app/globals.css");
    expect(api).toContain("page_size");
    expect(css).toMatch(/overflow-x:\s*auto/);
    expect(css).toContain("@media (max-width: 720px)");
    expect(css).not.toMatch(/body\s*\{[^}]*overflow-y:\s*hidden/s);
  });

  it("does not expose CMS, database or authentication secrets", () => {
    const sources = [
      "lib/content-api.ts", "components/content-editor.tsx",
      "components/category-manager.tsx", "app/api/admin/content/[...path]/route.ts"
    ].map(source).join("\n");
    expect(sources).not.toMatch(/localStorage|sessionStorage/);
    expect(sources).not.toMatch(/NEXT_PUBLIC_(JWT|DATABASE|SUPABASE|BFF|SESSION)/);
  });
});
