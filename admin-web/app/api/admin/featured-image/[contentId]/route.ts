import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { verifyCsrfToken } from "@/lib/csrf";
import { getAdminServerConfig } from "@/lib/server-config";
import { ADMIN_CSRF_COOKIE, ADMIN_SESSION_COOKIE } from "@/lib/session";

async function proxy(request: NextRequest, context: { params: Promise<{ contentId: string }> }) {
  if (!verifyCsrfToken(request.cookies.get(ADMIN_CSRF_COOKIE)?.value, request.headers.get("x-csrf-token"))) return NextResponse.json({ message: "Invalid request." }, { status: 403 });
  const token = request.cookies.get(ADMIN_SESSION_COOKIE)?.value || "";
  if (!token) return NextResponse.json({ message: "Authentication required." }, { status: 401 });
  const contentId = (await context.params).contentId;
  if (!/^\d+$/.test(contentId)) return NextResponse.json({ message: "Not found." }, { status: 404 });
  try {
    const config = getAdminServerConfig();
    const body = request.method === "POST" ? await request.text() : undefined;
    const upstream = await fetch(`${config.backendBaseUrl}/admin/content/${contentId}/featured-image`, {
      method: request.method, body, cache: "no-store", signal: AbortSignal.timeout(5000),
      headers: { Authorization: `Bearer ${token}`, "X-Admin-BFF-Key": config.bffSecret, "X-Request-ID": randomUUID(), ...(body ? { "Content-Type": "application/json" } : {}) }
    });
    return new NextResponse(await upstream.text() || null, { status: upstream.status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
  } catch { return NextResponse.json({ message: "Media service is temporarily unavailable." }, { status: 503 }); }
}

export const POST = proxy;
export const DELETE = proxy;
