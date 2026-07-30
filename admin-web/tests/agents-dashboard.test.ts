import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const root = join(process.cwd());

function read(relativePath: string): string {
  return readFileSync(join(root, relativePath), "utf8");
}

describe("Agents Dashboard", () => {
  it("registers Agents as an active protected workspace", () => {
    const navigation = read("components/admin-navigation.tsx");
    const page = read("app/admin/(protected)/agents/page.tsx");

    expect(navigation).toContain('["Agents", "/admin/agents", "✣"]');
    expect(page).toContain("fetchAgentsDashboard");
    expect(page).toContain("<AgentsDashboard");
  });

  it("uses the protected BFF route without exposing secrets", () => {
    const route = read("app/api/admin/agents/route.ts");

    expect(route).toContain("ADMIN_SESSION_COOKIE");
    expect(route).toContain('"X-Admin-BFF-Key": config.bffSecret');
    expect(route).toContain('cache: "no-store"');
    expect(route).not.toContain("ADMIN_BFF_SHARED_SECRET=");
  });

  it("keeps operational controls disabled in read-only mode", () => {
    const dashboard = read("components/agents-dashboard.tsx");

    expect(dashboard).toContain("Read-only safety mode");
    expect(dashboard).toContain("Controls coming later");
    expect(dashboard).toContain("<button type=\"button\" disabled>");
    expect(dashboard).not.toContain("fetch(\"/api/admin/agents/run");
  });

  it("contains responsive mobile dashboard styles", () => {
    const styles = read("app/globals.css");

    expect(styles).toContain("@media (max-width: 680px)");
    expect(styles).toContain(".agents-grid");
    expect(styles).toContain(".agent-action-grid");
  });
});
