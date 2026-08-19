import { NextResponse } from "next/server";
import { createCsrfToken } from "@/lib/csrf";
import { ADMIN_CSRF_COOKIE, csrfCookieOptions } from "@/lib/session";

export const dynamic = "force-dynamic";

export async function GET() {
  const token = createCsrfToken();
  const response = NextResponse.json({ csrfToken: token });
  response.cookies.set(ADMIN_CSRF_COOKIE, token, csrfCookieOptions());
  response.headers.set("Cache-Control", "no-store");
  return response;
}
