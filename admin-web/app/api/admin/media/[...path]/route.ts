import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { verifyCsrfToken } from "@/lib/csrf";
import { getAdminServerConfig } from "@/lib/server-config";
import { ADMIN_CSRF_COOKIE, ADMIN_SESSION_COOKIE } from "@/lib/session";

const allowedPath = /^(upload|\d+(\/(trash|restore))?)?$/;

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const path = (await context.params).path.join("/");
  if (!allowedPath.test(path)) return NextResponse.json({ message: "Not found." }, { status: 404 });
  const stateChanging = request.method !== "GET";
  if (stateChanging && !verifyCsrfToken(request.cookies.get(ADMIN_CSRF_COOKIE)?.value, request.headers.get("x-csrf-token"))) {
    return NextResponse.json({ message: "Invalid request." }, { status: 403 });
  }
  const token = request.cookies.get(ADMIN_SESSION_COOKIE)?.value || "";
  if (!token) return NextResponse.json({ message: "Authentication required." }, { status: 401 });
  try {
    const config = getAdminServerConfig();
    const contentType = request.headers.get("content-type") || "";
    const body = stateChanging ? await request.arrayBuffer() : undefined;
    const upstream = await fetch(`${config.backendBaseUrl}/admin/media${path ? `/${path}` : ""}${request.nextUrl.search}`, {
      method: request.method,
      headers: {
        Authorization: `Bearer ${token}`, "X-Admin-BFF-Key": config.bffSecret,
        "X-Request-ID": randomUUID(), ...(contentType ? { "Content-Type": contentType } : {})
      },
      body, cache: "no-store", signal: AbortSignal.timeout(15000)
    });
    return new NextResponse(await upstream.text() || null, { status: upstream.status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ message: "Media service is temporarily unavailable." }, { status: 503 });
  }
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
