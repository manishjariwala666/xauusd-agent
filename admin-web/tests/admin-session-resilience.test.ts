import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.cwd());

function read(rel: string) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

describe("Admin session resilience", () => {
  it("uses a safer backend session timeout", () => {
    const source = read("lib/admin-api.ts");
    expect(source).toContain("AbortSignal.timeout(10000)");
  });

  it("returns 503 for unavailable session validation", () => {
    const source = read("app/api/admin/auth/session/route.ts");
    expect(source).toContain('result.status === "unavailable"');
    expect(source).toContain("? 503");
  });

  it("clears session cookie only for unauthenticated sessions", () => {
    const source = read("app/api/admin/auth/session/route.ts");
    expect(source).toContain(
      'if (result.status === "unauthenticated")'
    );
    expect(source).not.toContain("if (status === 401)");
  });

  it("does not redirect transient admin session failures to login", () => {
    const source = read("app/admin/(protected)/layout.tsx");
    expect(source).toContain(
      'if (result.status === "unavailable")'
    );
    expect(source).toContain(
      "Your session has not been cleared."
    );
  });

  it("does not redirect transient Studio V2 session failures to login", () => {
    const source = read("app/studio-v2/layout.tsx");
    expect(source).toContain(
      'if (result.status === "unavailable")'
    );
    expect(source).toContain(
      "Your session has not been cleared."
    );
  });
});
