import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const DEFAULT_API_BASE =
  "https://venusrealm-master-ai-682301080982.asia-south1.run.app";
const API_BASE = (process.env.BACKEND_BASE_URL?.trim() || DEFAULT_API_BASE).replace(/\/$/, "");
const SESSION_COOKIE = "vr_member_session";

const PUBLIC_POST_PATHS = new Set([
  "auth/signup",
  "auth/login",
  "auth/resend-verification",
  "auth/verify-email",
  "auth/forgot-password",
  "auth/reset-password",
]);
const AUTHENTICATED_PATHS = new Set([
  "auth/me",
  "payment",
  "payment/submit",
  "access",
]);

function isAllowed(path: string, method: string): boolean {
  if (path === "auth/logout" && method === "POST") return true;
  if (PUBLIC_POST_PATHS.has(path)) return method === "POST";
  if (AUTHENTICATED_PATHS.has(path)) {
    return (path === "payment/submit" ? method === "POST" : method === "GET");
  }
  if (path === "signals" || path.startsWith("signals/")) return method === "GET";
  return false;
}

async function handler(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const { path: parts } = await context.params;
  const path = (parts || []).join("/");
  if (!isAllowed(path, request.method)) {
    return NextResponse.json({ detail: "Member route not found." }, { status: 404 });
  }

  const cookieStore = await cookies();
  if (path === "auth/logout") {
    const response = NextResponse.json({ logged_out: true });
    response.cookies.set(SESSION_COOKIE, "", {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    });
    return response;
  }

  const session = cookieStore.get(SESSION_COOKIE)?.value;
  const isPublicPost = PUBLIC_POST_PATHS.has(path);
  if (!isPublicPost && !session) {
    return NextResponse.json({ detail: "Authentication required." }, { status: 401 });
  }

  const headers = new Headers({ Accept: "application/json" });
  if (request.method !== "GET") headers.set("Content-Type", "application/json");
  if (session && !isPublicPost) headers.set("Authorization", `Bearer ${session}`);

  const query = request.nextUrl.search;
  const upstreamUrl = `${API_BASE}/api/v1/member/${path}${query}`;
  let body: string | undefined;
  if (request.method !== "GET") body = await request.text();

  let upstream: Response;
  try {
    upstream = await fetch(upstreamUrl, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(8000),
    });
  } catch {
    return NextResponse.json(
      { detail: "Member service is temporarily unavailable." },
      { status: 503 }
    );
  }

  const payload = await upstream.json().catch(() => ({ detail: "Invalid upstream response." }));
  const responsePayload = { ...payload } as Record<string, unknown>;
  const response = NextResponse.json(responsePayload, { status: upstream.status });
  response.headers.set("Cache-Control", "private, no-store");

  if (path === "auth/login" && upstream.ok && typeof responsePayload.access_token === "string") {
    const token = responsePayload.access_token;
    delete responsePayload.access_token;
    const sanitized = NextResponse.json(responsePayload, { status: upstream.status });
    sanitized.headers.set("Cache-Control", "private, no-store");
    sanitized.cookies.set(SESSION_COOKIE, token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 12,
    });
    return sanitized;
  }

  if (upstream.status === 401 && session) {
    response.cookies.set(SESSION_COOKIE, "", {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    });
  }
  return response;
}

export const GET = handler;
export const POST = handler;
