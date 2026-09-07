import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { verifyCsrfToken } from "@/lib/csrf";
import { getAdminServerConfig } from "@/lib/server-config";
import {
  ADMIN_CSRF_COOKIE,
  ADMIN_SESSION_COOKIE,
} from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  if (
    !verifyCsrfToken(
      request.cookies.get(ADMIN_CSRF_COOKIE)?.value,
      request.headers.get("x-csrf-token"),
    )
  ) {
    return NextResponse.json(
      { message: "Invalid request." },
      { status: 403 },
    );
  }

  const cookieStore = await cookies();
  const token =
    request.cookies.get(ADMIN_SESSION_COOKIE)?.value ||
    cookieStore.get(ADMIN_SESSION_COOKIE)?.value;

  if (!token) {
    return NextResponse.json(
      { message: "Authentication required." },
      { status: 401 },
    );
  }

  const config = getAdminServerConfig();

  try {
    const response = await fetch(
      `${config.backendBaseUrl}/admin/content-studio/ai-suggestions`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "X-Admin-BFF-Key": config.bffSecret,
          "X-Request-ID": randomUUID(),
        },
        body: await request.text(),
        cache: "no-store",
        signal: AbortSignal.timeout(130_000),
      },
    );

    return new NextResponse(await response.text(), {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("content-type") ||
          "application/json",
        "Cache-Control": "private, no-store",
      },
    });
  } catch {
    return NextResponse.json(
      {
        message:
          "AI suggestions are temporarily unavailable. Existing content was not changed.",
      },
      { status: 503 },
    );
  }
}
