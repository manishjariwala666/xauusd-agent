import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { verifyCsrfToken } from "@/lib/csrf";
import { getAdminServerConfig } from "@/lib/server-config";
import {
  ADMIN_CSRF_COOKIE,
  ADMIN_SESSION_COOKIE,
  sessionCookieOptions
} from "@/lib/session";

type BackendLogin = {
  access_token: string;
  expires_at: string;
  user: { user_id: number; email: string; role: string };
};

export async function POST(request: NextRequest) {
  if (!verifyCsrfToken(
    request.cookies.get(ADMIN_CSRF_COOKIE)?.value,
    request.headers.get("x-csrf-token")
  )) {
    return NextResponse.json({ message: "Invalid request." }, { status: 403 });
  }
  let credentials: { email?: string; password?: string };
  try {
    credentials = await request.json();
  } catch {
    return NextResponse.json({ message: "Invalid request." }, { status: 400 });
  }
  if (!credentials.email || !credentials.password) {
    return NextResponse.json({ message: "Email and password are required." }, { status: 400 });
  }
  try {
    const config = getAdminServerConfig();
    const upstream = await fetch(`${config.backendBaseUrl}/admin/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-BFF-Key": config.bffSecret,
        "X-Request-ID": randomUUID(),
        "X-Forwarded-For": request.headers.get("x-forwarded-for") || "unknown",
        "User-Agent": request.headers.get("user-agent") || "admin-web"
      },
      body: JSON.stringify({ email: credentials.email, password: credentials.password }),
      cache: "no-store",
      signal: AbortSignal.timeout(5000)
    });
    if (!upstream.ok) {
      const status = upstream.status === 429
        ? 429
        : upstream.status === 403
          ? 403
          : upstream.status >= 500
            ? 503
            : 401;
      return NextResponse.json(
        {
          message: status === 429
            ? "Too many attempts. Try again later."
            : status === 503
              ? "Admin login is temporarily unavailable."
              : "Invalid email or password."
        },
        { status, headers: status === 429 ? { "Retry-After": upstream.headers.get("retry-after") || "900" } : undefined }
      );
    }
    const payload = (await upstream.json()) as BackendLogin;
    if (!payload.access_token || payload.user?.role !== "ADMIN") {
      return NextResponse.json({ message: "Administrator access is forbidden." }, { status: 403 });
    }
    const expiresIn = Math.floor((new Date(payload.expires_at).getTime() - Date.now()) / 1000);
    const response = NextResponse.json({ user: payload.user });
    response.cookies.set(ADMIN_SESSION_COOKIE, payload.access_token, sessionCookieOptions(expiresIn));
    response.headers.set("Cache-Control", "no-store");
    return response;
  } catch {
    return NextResponse.json({ message: "Admin login is temporarily unavailable." }, { status: 503 });
  }
}
