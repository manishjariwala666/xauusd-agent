import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

import { verifyCsrfToken } from "@/lib/csrf";
import { getAdminServerConfig } from "@/lib/server-config";
import {
  ADMIN_CSRF_COOKIE,
  ADMIN_SESSION_COOKIE,
} from "@/lib/session";

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

  const token =
    request.cookies.get(ADMIN_SESSION_COOKIE)?.value || "";

  if (!token) {
    return NextResponse.json(
      { message: "Authentication required." },
      { status: 401 },
    );
  }

  let body: string;

  try {
    body = JSON.stringify(await request.json());
  } catch {
    return NextResponse.json(
      { message: "Invalid JSON payload." },
      { status: 400 },
    );
  }

  try {
    const config = getAdminServerConfig();

    const upstream = await fetch(
      `${config.backendBaseUrl}/admin/agents/builder/preview`,
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
        signal: AbortSignal.timeout(10000),
      },
    );

    return new NextResponse(
      (await upstream.text()) || null,
      {
        status: upstream.status,
        headers: {
          "Content-Type": "application/json",
          "Cache-Control": "no-store",
        },
      },
    );
  } catch {
    return NextResponse.json(
      {
        message:
          "Agent Builder service is temporarily unavailable.",
      },
      { status: 503 },
    );
  }
}
