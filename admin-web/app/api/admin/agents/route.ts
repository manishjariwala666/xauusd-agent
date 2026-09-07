import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { getAdminServerConfig } from "@/lib/server-config";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

export async function GET(request: NextRequest) {
  const token = request.cookies.get(ADMIN_SESSION_COOKIE)?.value || "";

  if (!token) {
    return NextResponse.json(
      { message: "Authentication required." },
      { status: 401 }
    );
  }

  try {
    const config = getAdminServerConfig();
    const upstream = await fetch(`${config.backendBaseUrl}/admin/agents`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Admin-BFF-Key": config.bffSecret,
        "X-Request-ID": randomUUID()
      },
      cache: "no-store",
      signal: AbortSignal.timeout(8000)
    });

    return new NextResponse(await upstream.text() || null, {
      status: upstream.status,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store"
      }
    });
  } catch {
    return NextResponse.json(
      { message: "Agents service is temporarily unavailable." },
      { status: 503 }
    );
  }
}
