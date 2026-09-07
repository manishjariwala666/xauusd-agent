import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { getAdminServerConfig } from "@/lib/server-config";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
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
  const params = await context.params;
  const safePath = params.path
    .map(part => encodeURIComponent(decodeURIComponent(part)))
    .join("/");

  try {
    const response = await fetch(
      `${config.backendBaseUrl}/${safePath}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Admin-BFF-Key": config.bffSecret,
        },
        cache: "no-store",
        signal: AbortSignal.timeout(20_000),
      },
    );

    if (!response.ok) {
      return NextResponse.json(
        { message: "Image file is unavailable." },
        { status: response.status },
      );
    }

    return new NextResponse(response.body, {
      status: 200,
      headers: {
        "Content-Type":
          response.headers.get("content-type") ||
          "application/octet-stream",
        "Cache-Control": "private, max-age=60",
      },
    });
  } catch {
    return NextResponse.json(
      { message: "Image preview is temporarily unavailable." },
      { status: 502 },
    );
  }
}
