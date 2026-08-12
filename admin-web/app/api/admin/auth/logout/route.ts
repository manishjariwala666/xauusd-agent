import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { verifyCsrfToken } from "@/lib/csrf";
import { getAdminServerConfig } from "@/lib/server-config";
import { ADMIN_CSRF_COOKIE, ADMIN_SESSION_COOKIE, sessionCookieOptions } from "@/lib/session";

export async function POST(request: NextRequest) {
  if (!verifyCsrfToken(
    request.cookies.get(ADMIN_CSRF_COOKIE)?.value,
    request.headers.get("x-csrf-token")
  )) {
    return NextResponse.json({ message: "Invalid request." }, { status: 403 });
  }
  const token = request.cookies.get(ADMIN_SESSION_COOKIE)?.value || "";
  if (token) {
    try {
      const config = getAdminServerConfig();
      await fetch(`${config.backendBaseUrl}/admin/auth/logout`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Admin-BFF-Key": config.bffSecret,
          "X-Request-ID": randomUUID(),
          "X-Forwarded-For": request.headers.get("x-forwarded-for") || "unknown",
          "User-Agent": request.headers.get("user-agent") || "admin-web"
        },
        cache: "no-store",
        signal: AbortSignal.timeout(3000)
      });
    } catch {
      // Cookie removal remains safe even when the upstream service is degraded.
    }
  }
  const response = NextResponse.json({ loggedOut: true });
  response.cookies.set(ADMIN_SESSION_COOKIE, "", sessionCookieOptions(0));
  response.headers.set("Cache-Control", "no-store");
  return response;
}
