import { randomBytes, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

const COOKIE = "vr_lead_csrf";
const BACKEND = (process.env.BACKEND_BASE_URL || "https://xauusd-agent-api-production.up.railway.app").replace(/\/$/, "");

export function GET() {
  const token = randomBytes(24).toString("base64url");
  const response = NextResponse.json({ csrfToken: token }, { headers: { "Cache-Control": "no-store" } });
  response.cookies.set(COOKIE, token, { httpOnly: true, secure: true, sameSite: "strict", path: "/", maxAge: 600 });
  return response;
}

export async function POST(request: NextRequest) {
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host") || "";
  const protocol = request.headers.get("x-forwarded-proto") || request.nextUrl.protocol.replace(":", "") || "https";
  const expectedOrigin = `${protocol}://${host}`;
  if (request.headers.get("origin") !== expectedOrigin) return NextResponse.json({ message: "Invalid request origin." }, { status: 403 });
  const cookie = request.cookies.get(COOKIE)?.value || "";
  const supplied = request.headers.get("x-csrf-token") || "";
  if (!cookie || cookie.length !== supplied.length || !timingSafeEqual(Buffer.from(cookie), Buffer.from(supplied))) return NextResponse.json({ message: "Invalid request token." }, { status: 403 });
  try {
    const body = await request.text();
    if (Buffer.byteLength(body) > 30_000) return NextResponse.json({ message: "Request is too large." }, { status: 413 });
    const response = await fetch(`${BACKEND}/public/automation-enquiries`, { method: "POST", headers: { "Content-Type": "application/json", "X-Forwarded-For": request.headers.get("x-forwarded-for") || "" }, body, cache: "no-store", signal: AbortSignal.timeout(5000) });
    return new NextResponse(await response.text(), { status: response.status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ message: "Enquiry service is temporarily unavailable." }, { status: 503 });
  }
}
