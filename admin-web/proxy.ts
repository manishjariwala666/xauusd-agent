import { NextRequest, NextResponse } from "next/server";
import { isProtectedAdminPath } from "@/lib/access-control";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasSession = Boolean(request.cookies.get(ADMIN_SESSION_COOKIE)?.value);
  if (isProtectedAdminPath(pathname) && !hasSession) {
    return NextResponse.redirect(new URL("/admin/login", request.url));
  }
  if (pathname === "/admin/login" && hasSession) {
    return NextResponse.redirect(new URL("/admin/dashboard", request.url));
  }
  return NextResponse.next();
}

export const config = { matcher: ["/admin/:path*"] };
