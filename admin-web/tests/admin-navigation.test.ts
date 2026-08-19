import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();

function exists(rel: string) {
  return fs.existsSync(path.join(root, rel));
}

function read(rel: string) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

describe("Admin navigation", () => {
  it("maps every active legacy sidebar destination to a real page", () => {
    const routes = [
      ["Dashboard", "app/admin/(protected)/dashboard/page.tsx"],
      ["Blog Studio", "app/admin/(protected)/posts/page.tsx"],
      ["Pages", "app/admin/(protected)/pages/page.tsx"],
      ["Categories", "app/admin/(protected)/categories/page.tsx"],
      ["Media", "app/admin/(protected)/media/page.tsx"],
      ["SEO", "app/admin/(protected)/seo/page.tsx"],
      ["Signals", "app/admin/(protected)/signals/page.tsx"],
      ["Announcements", "app/admin/(protected)/announcements/page.tsx"],
      ["Verified Results", "app/admin/(protected)/results/page.tsx"],
      ["Leads", "app/admin/(protected)/leads/page.tsx"],
      ["Agents", "app/admin/(protected)/agents/page.tsx"],
      ["Master AI", "app/studio-v2/master-ai/page.tsx"],
    ];

    for (const [label, route] of routes) {
      expect(exists(route), `${label} route missing`).toBe(true);
    }
  });

  it("exposes Master AI from the main admin sidebar", () => {
    const source = read("components/admin-navigation.tsx");

    expect(source).toContain('"Master AI"');
    expect(source).toContain('"/studio-v2/master-ai"');
  });

  it("keeps unfinished tools explicitly disabled", () => {
    const source = read("components/admin-navigation.tsx");

    expect(source).toContain('aria-disabled="true"');
    expect(source).toContain("Coming later");
  });
});
