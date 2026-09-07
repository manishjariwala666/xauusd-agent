import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "node:crypto";
import { verifyCsrfToken } from "@/lib/csrf";
import { getAdminServerConfig } from "@/lib/server-config";
import { ADMIN_CSRF_COOKIE, ADMIN_SESSION_COOKIE } from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  if (!verifyCsrfToken(
    request.cookies.get(ADMIN_CSRF_COOKIE)?.value,
    request.headers.get("x-csrf-token"),
  )) {
    return NextResponse.json({ message: "Invalid request." }, { status: 403 });
  }

  const config = getAdminServerConfig();
  const token = request.cookies.get(ADMIN_SESSION_COOKIE)?.value;

  if (!token) {
    return NextResponse.json({ message: "Authentication required." }, { status: 401 });
  }

  try {
    const body = await request.text();
    const response = await fetch(
      `${config.backendBaseUrl}/admin/content-studio/seo-preview`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "X-Admin-BFF-Key": config.bffSecret,
          "X-Request-ID": randomUUID(),
        },
        body,
        cache: "no-store",
        signal: AbortSignal.timeout(15_000),
      },
    );

    return new NextResponse(await response.text(), {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") || "application/json",
        "Cache-Control": "private, no-store",
      },
    });
  } catch {
    return NextResponse.json(
      { message: "Live SEO preview is temporarily unavailable." },
      { status: 503 },
    );
  }
}
