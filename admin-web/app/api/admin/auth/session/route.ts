import { NextRequest, NextResponse } from "next/server";
import { fetchAdminSession } from "@/lib/admin-api";
import { ADMIN_SESSION_COOKIE, sessionCookieOptions } from "@/lib/session";

export async function GET(request: NextRequest) {
  const result = await fetchAdminSession(request.cookies.get(ADMIN_SESSION_COOKIE)?.value || "");
  const status =
    result.status === "authenticated"
      ? 200
      : result.status === "forbidden"
        ? 403
        : result.status === "unavailable"
          ? 503
          : 401;

  const response = NextResponse.json(result, { status });

  if (result.status === "unauthenticated") {
    response.cookies.set(
      ADMIN_SESSION_COOKIE,
      "",
      sessionCookieOptions(0),
    );
  }
  response.headers.set("Cache-Control", "no-store");
  return response;
}
