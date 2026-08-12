import { NextRequest, NextResponse } from "next/server";
import { getAdminServerConfig } from "@/lib/server-config";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";
import { normalizeMediaPayloadUrls } from "@/lib/media-url";

export async function GET(request: NextRequest) {
  const token = request.cookies.get(ADMIN_SESSION_COOKIE)?.value || "";
  if (!token) return NextResponse.json({ message: "Authentication required." }, { status: 401 });
  try {
    const config = getAdminServerConfig();
    const upstream = await fetch(`${config.backendBaseUrl}/admin/media${request.nextUrl.search}`, {
      headers: { Authorization: `Bearer ${token}`, "X-Admin-BFF-Key": config.bffSecret }, cache: "no-store", signal: AbortSignal.timeout(5000)
    });
    const rawBody = await upstream.text();
    if (!rawBody) {
      return new NextResponse(null, {
        status: upstream.status,
        headers: { "Cache-Control": "no-store" },
      });
    }

    let payload: unknown;
    try {
      payload = JSON.parse(rawBody);
    } catch {
      return NextResponse.json(
        { message: "Media service returned an invalid response." },
        { status: 502, headers: { "Cache-Control": "no-store" } },
      );
    }

    const publicOrigin = request.nextUrl.origin;
    const normalized = normalizeMediaPayloadUrls(
      payload,
      config.backendBaseUrl,
      `${publicOrigin}/media-fallback.svg`,
    );
    return NextResponse.json(normalized, {
      status: upstream.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch { return NextResponse.json({ message: "Media service is temporarily unavailable." }, { status: 503 }); }
}
