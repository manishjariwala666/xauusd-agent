import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

import { verifyCsrfToken } from "@/lib/csrf";
import { getAdminServerConfig } from "@/lib/server-config";
import {
  ADMIN_CSRF_COOKIE,
  ADMIN_SESSION_COOKIE,
} from "@/lib/session";

export async function POST(
  request: NextRequest,
  context: {
    params: Promise<{ agentKey: string }>;
  },
) {
  const { agentKey } = await context.params;

  if (agentKey !== "ai_blog_agent") {
    return NextResponse.json(
      {
        message:
          "Only AI Blog Agent control is enabled in this phase.",
      },
      { status: 403 },
    );
  }

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

  let payload: { enabled?: unknown };

  try {
    payload = (await request.json()) as {
      enabled?: unknown;
    };
  } catch {
    return NextResponse.json(
      { message: "Invalid JSON payload." },
      { status: 400 },
    );
  }

  if (typeof payload.enabled !== "boolean") {
    return NextResponse.json(
      { message: "Enabled must be a boolean." },
      { status: 422 },
    );
  }

  try {
    const config = getAdminServerConfig();

    const upstream = await fetch(
      `${config.backendBaseUrl}/admin/agents/${agentKey}/enabled`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "X-Admin-BFF-Key": config.bffSecret,
          "X-Request-ID": randomUUID(),
        },
        body: JSON.stringify({
          enabled: payload.enabled,
        }),
        cache: "no-store",
        signal: AbortSignal.timeout(8000),
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
          "Agent control service is temporarily unavailable.",
      },
      { status: 503 },
    );
  }
}
