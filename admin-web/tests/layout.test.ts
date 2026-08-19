import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const root = resolve(import.meta.dirname, "..");
const source = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("responsive Phase 1 shell", () => {
  it("includes sidebar, topbar and breadcrumbs", () => {
    const shell = source("components/admin-shell.tsx") + source("components/admin-navigation.tsx");
    expect(shell).toContain("Admin navigation");
    expect(shell).toContain('className="topbar"');
    expect(shell).toContain('className="breadcrumbs"');
  });

  it("keeps future modules disabled and unloaded", () => {
    const shell = source("components/admin-shell.tsx") + source("components/admin-navigation.tsx");
    const dashboard = source("app/admin/(protected)/dashboard/page.tsx");
    expect(shell).toContain('aria-disabled="true"');
    expect(dashboard).toContain("intentionally not loaded");
  });

  it("supports desktop and mobile without horizontal page overflow", () => {
    const css = source("app/globals.css");
    expect(css).toMatch(/grid-template-columns:\s*264px minmax\(0,\s*1fr\)/);
    expect(css).toContain("@media (max-width: 720px)");
    expect(css).toMatch(/overflow-x:\s*hidden/);
    expect(css).not.toMatch(/body\s*\{[^}]*overflow-y:\s*hidden/s);
    expect(css).toMatch(/overflow-y:\s*auto/);
  });

  it("provides loading, empty, error and not-found states", () => {
    expect(source("components/states.tsx")).toContain("EmptyState");
    expect(source("app/admin/(protected)/loading.tsx")).toContain("LoadingState");
    expect(source("app/admin/(protected)/error.tsx")).toContain("Admin panel could not be loaded");
    expect(source("app/not-found.tsx")).toContain("Admin page not found");
  });
});
