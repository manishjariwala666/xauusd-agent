import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { createCsrfToken, verifyCsrfToken } from "@/lib/csrf";
import { isProtectedAdminPath } from "@/lib/access-control";
import {
  ADMIN_SESSION_MAX_AGE_SECONDS,
  csrfCookieOptions,
  sessionCookieOptions
} from "@/lib/session";

const root = resolve(import.meta.dirname, "..");
const source = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("Phase 1 security controls", () => {
  it("protects every admin route except login and forbidden", () => {
    expect(isProtectedAdminPath("/admin")).toBe(true);
    expect(isProtectedAdminPath("/admin/dashboard")).toBe(true);
    expect(isProtectedAdminPath("/admin/login")).toBe(false);
    expect(isProtectedAdminPath("/admin/forbidden")).toBe(false);
  });

  it("uses short-lived Secure HttpOnly SameSite cookies", () => {
    expect(sessionCookieOptions()).toMatchObject({
      httpOnly: true,
      secure: true,
      sameSite: "lax",
      path: "/",
      maxAge: ADMIN_SESSION_MAX_AGE_SECONDS
    });
    expect(ADMIN_SESSION_MAX_AGE_SECONDS).toBeLessThanOrEqual(15 * 60);
    expect(csrfCookieOptions()).toMatchObject({ httpOnly: true, secure: true, sameSite: "lax" });
  });

  it("rejects missing and mismatched CSRF tokens", () => {
    const token = createCsrfToken();
    expect(token.length).toBeGreaterThanOrEqual(40);
    expect(verifyCsrfToken(token, token)).toBe(true);
    expect(verifyCsrfToken(token, `${token}x`)).toBe(false);
    expect(verifyCsrfToken(undefined, token)).toBe(false);
  });

  it("keeps browser code free from token storage and public secrets", () => {
    const browserFiles = [
      "components/login-form.tsx",
      "components/logout-button.tsx",
      "app/api/admin/auth/login/route.ts",
      "lib/server-config.ts"
    ].map(source).join("\n");
    expect(browserFiles).not.toMatch(/localStorage|sessionStorage/);
    expect(browserFiles).not.toMatch(/NEXT_PUBLIC_(JWT|DATABASE|SUPABASE|SMTP|TELEGRAM|AI|SESSION)/);
    expect(source(".env.example")).not.toMatch(/JWT_SECRET|DATABASE_URL|SUPABASE_SERVICE|TELEGRAM_TOKEN/);
  });

  it("requires BFF and database session revalidation", () => {
    const api = source("lib/admin-api.ts");
    const layout = source("app/admin/(protected)/layout.tsx");
    expect(api).toContain("X-Admin-BFF-Key");
    expect(api).toContain("/admin/auth/session");
    expect(api).toContain('role !== "ADMIN"');
    expect(layout).toContain("fetchAdminSession(token)");
    expect(layout).toContain('redirect("/admin/login")');
    expect(layout).toContain('redirect("/admin/forbidden")');
  });

  it("applies CSRF checks to login and logout", () => {
    expect(source("app/api/admin/auth/login/route.ts")).toContain("verifyCsrfToken");
    expect(source("app/api/admin/auth/logout/route.ts")).toContain("verifyCsrfToken");
  });

  it("keeps media storage authority server-side", () => {
    const browserMedia = [
      source("components/media-library.tsx"),
      source("components/featured-image-picker.tsx"),
      source("app/api/admin/media/[...path]/route.ts")
    ].join("\n");
    expect(browserMedia).not.toMatch(/SUPABASE_SERVICE_ROLE|DATABASE_URL|storage\.from/);
    expect(browserMedia).not.toContain("base64");
  });
});
