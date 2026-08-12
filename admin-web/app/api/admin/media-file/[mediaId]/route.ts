import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { getAdminServerConfig } from "@/lib/server-config";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

const MEDIA_ID = /^\d+$/;

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ mediaId: string }> },
) {
  const token = request.cookies.get(ADMIN_SESSION_COOKIE)?.value || "";
  if (!token) {
    return NextResponse.json(
      { message: "Authentication required." },
      { status: 401 },
    );
  }

  const { mediaId } = await context.params;
  const requestedVariant = request.nextUrl.searchParams.get("variant") || "original";
  if (!MEDIA_ID.test(mediaId) || !["original", "thumbnail"].includes(requestedVariant)) {
    return NextResponse.json({ message: "Not found." }, { status: 404 });
  }

  try {
    const config = getAdminServerConfig();
    const variants = requestedVariant === "thumbnail"
      ? ["thumbnail", "original"]
      : ["original"];
    let lastStatus = 404;

    for (const variant of variants) {
      const upstream = await fetch(
        `${config.backendBaseUrl}/admin/media/${mediaId}/file?variant=${variant}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "X-Admin-BFF-Key": config.bffSecret,
            "X-Request-ID": randomUUID(),
          },
          cache: "no-store",
          signal: AbortSignal.timeout(15_000),
        },
      );

      lastStatus = upstream.status;
      if (!upstream.ok) {
        if (variant === "thumbnail" && upstream.status === 404) continue;
        break;
      }

      const contentType = upstream.headers.get("content-type") || "";
      if (!contentType.toLowerCase().startsWith("image/")) {
        return NextResponse.json(
          { message: "Media service returned an invalid file." },
          { status: 502 },
        );
      }

      return new NextResponse(await upstream.arrayBuffer(), {
        status: 200,
        headers: {
          "Content-Type": contentType,
          "Cache-Control": "private, no-store",
          "X-Content-Type-Options": "nosniff",
        },
      });
    }

    return NextResponse.json(
      { message: lastStatus === 404 ? "Media file was not found." : "Media service is temporarily unavailable." },
      { status: lastStatus === 404 ? 404 : 502 },
    );
  } catch {
    return NextResponse.json(
      { message: "Media service is temporarily unavailable." },
      { status: 503 },
    );
  }
}
