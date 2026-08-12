import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const root = resolve(import.meta.dirname, "..");
const source = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("Signals Admin", () => {
  it("enables the module and provides list, new, and edit routes", () => {
    expect(source("components/admin-navigation.tsx")).toContain('["Signals", "/admin/signals"');
    for (const route of ["app/admin/(protected)/signals/page.tsx", "app/admin/(protected)/signals/new/page.tsx", "app/admin/(protected)/signals/[id]/edit/page.tsx"]) {
      expect(() => source(route)).not.toThrow();
    }
  });

  it("keeps browser mutations behind CSRF and the narrow BFF route", () => {
    const bff = source("app/api/admin/signals/[...path]/route.ts");
    expect(bff).toContain("verifyCsrfToken");
    expect(bff).toContain("allowedPath");
    expect(bff).toContain("ADMIN_SESSION_COOKIE");
    expect(bff).toContain("X-Admin-BFF-Key");
    expect(bff).not.toContain("NEXT_PUBLIC_ADMIN_BFF");
  });

  it("renders filters, pagination, empty state, and confirmed lifecycle actions", () => {
    const list = source("components/signals-dashboard.tsx");
    const actions = source("components/signal-actions.tsx");
    for (const feature of ["Signal filters", "No signals match", "Signals pagination", "direction", "timeframe"]) expect(list).toContain(feature);
    expect(actions).toContain("window.confirm");
    expect(actions).toContain('action: "TARGET_HIT"');
  });

  it("provides a responsive two-column editor and factual preview", () => {
    const editor = source("components/signal-editor.tsx");
    expect(editor).toContain("editor-grid");
    expect(editor).toContain("Public preview");
    expect(editor).toContain("No live broker prices are fetched here");
    expect(editor).toContain("BUY");
    expect(editor).toContain("SELL");
  });

  it("marks an explicitly configured local QA environment", () => {
    const layout = source("app/admin/(protected)/layout.tsx");
    const shell = source("components/admin-shell.tsx");
    expect(layout).toContain('ADMIN_LOCAL_QA_MODE === "true"');
    expect(shell).toContain("LOCAL QA · SYNTHETIC DATA");
    expect(shell).toContain("Not live market information");
  });
});
