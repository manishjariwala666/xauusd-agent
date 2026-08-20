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

  it("treats BFF authorization failure as infrastructure unavailable", () => {
    const source = read("lib/admin-api.ts");
    expect(source).toContain('detail === "Administrator access is forbidden."');
    expect(source).toContain('return { status: "unavailable" };');
  });

  it("redirects login only for an explicit account access denial", () => {
    const route = read("app/api/admin/auth/login/route.ts");
    const form = read("components/login-form.tsx");
    expect(route).toContain('code: "ADMIN_ACCESS_FORBIDDEN"');
    expect(route).toContain('code: status === 503 ? "ADMIN_AUTH_UNAVAILABLE"');
    expect(form).toContain('payload.code === "ADMIN_ACCESS_FORBIDDEN"');
    expect(form).not.toContain('if (response.status === 403) {');
  });

  it("uses the canonical production API when Netlify omits BACKEND_BASE_URL", () => {
    const source = read("lib/server-config.ts");
    expect(source).toContain(
      'DEFAULT_PRODUCTION_BACKEND_BASE_URL = "https://api.venusrealm.net"'
    );
    expect(source).toContain(
      "process.env.BACKEND_BASE_URL || DEFAULT_PRODUCTION_BACKEND_BASE_URL"
    );
    expect(source).toContain("ADMIN_BFF_SHARED_SECRET");
  });
});
