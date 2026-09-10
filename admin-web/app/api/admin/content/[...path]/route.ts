import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { verifyCsrfToken } from "@/lib/csrf";
import { getAdminServerConfig } from "@/lib/server-config";
import { ADMIN_CSRF_COOKIE, ADMIN_SESSION_COOKIE } from "@/lib/session";

const allowedPath = /^(posts\/(?:plan-ai-draft|generate-ai-draft|generate-pdf-draft)|posts|pages)(\/\d+(\/(publish|unpublish|trash|duplicate|repair-preview|repair-apply))?)?$|^categories(\/\d+(\/disable)?)?$/;
const CMS_DOCUMENT_PATTERN = /<!--venusrealm-cms-v2:([^]*?)-->/;

type CmsImageSelection = {
  present: boolean;
  mediaId: number | null;
};

function cmsFeaturedImage(body?: string): CmsImageSelection {
  if (!body) return { present: false, mediaId: null };
  const match = body.match(CMS_DOCUMENT_PATTERN);
  if (!match?.[1]) return { present: false, mediaId: null };

  try {
    const document = JSON.parse(decodeURIComponent(match[1])) as {
      featuredMediaId?: unknown;
    };
    if (!("featuredMediaId" in document)) {
      return { present: false, mediaId: null };
    }
    const value = document.featuredMediaId;
    if (value === null || value === undefined || value === "") {
      return { present: true, mediaId: null };
    }
    const mediaId = Number(value);
    return Number.isInteger(mediaId) && mediaId > 0
      ? { present: true, mediaId }
      : { present: false, mediaId: null };
  } catch {
    return { present: false, mediaId: null };
  }
}

async function syncFeaturedImage(options: {
  backendBaseUrl: string;
  contentId: number;
  selection: CmsImageSelection;
  token: string;
  bffSecret: string;
}) {
  const { backendBaseUrl, contentId, selection, token, bffSecret } = options;
  if (!selection.present) return;

  const response = await fetch(
    `${backendBaseUrl}/admin/content/${contentId}/featured-image`,
    {
      method: selection.mediaId ? "POST" : "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Admin-BFF-Key": bffSecret,
        "X-Request-ID": randomUUID(),
        ...(selection.mediaId ? { "Content-Type": "application/json" } : {}),
      },
      body: selection.mediaId
        ? JSON.stringify({ media_id: selection.mediaId })
        : undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    },
  );

  if (!response.ok) {
    throw new Error("Featured image association failed.");
  }
}

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const path = (await context.params).path.join("/");
  if (!allowedPath.test(path)) return NextResponse.json({ message: "Not found." }, { status: 404 });
  const stateChanging = request.method !== "GET";
  if (stateChanging && !verifyCsrfToken(
    request.cookies.get(ADMIN_CSRF_COOKIE)?.value,
    request.headers.get("x-csrf-token")
  )) return NextResponse.json({ message: "Invalid request." }, { status: 403 });
  const token = request.cookies.get(ADMIN_SESSION_COOKIE)?.value || "";
  if (!token) return NextResponse.json({ message: "Authentication required." }, { status: 401 });
  try {
    const config = getAdminServerConfig();
    const query = request.nextUrl.search;
    const body = stateChanging ? await request.text() : undefined;
    const upstream = await fetch(`${config.backendBaseUrl}/admin/content/${path}${query}`, {
      method: request.method,
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Admin-BFF-Key": config.bffSecret,
        "X-Request-ID": randomUUID(),
        ...(body ? { "Content-Type": "application/json" } : {})
      },
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(
        path === "posts/plan-ai-draft"
          ? 60000
          : path === "posts/generate-ai-draft" || path === "posts/generate-pdf-draft" || path.endsWith("/repair-preview")
            ? 120000
            : 5000
      )
    });
    const payload = await upstream.text();

    if (
      upstream.ok &&
      (request.method === "POST" || request.method === "PATCH") &&
      (path === "posts" || /^posts\/\d+$/.test(path)) &&
      body
    ) {
      try {
        const requestPayload = JSON.parse(body) as { body?: string };
        const responsePayload = payload ? JSON.parse(payload) as { id?: number } : {};
        const contentId = Number(responsePayload.id || 0);
        const selection = cmsFeaturedImage(requestPayload.body);
        if (contentId > 0 && selection.present) {
          await syncFeaturedImage({
            backendBaseUrl: config.backendBaseUrl,
            contentId,
            selection,
            token,
            bffSecret: config.bffSecret,
          });
        }
      } catch (error) {
        if (error instanceof Error && error.message === "Featured image association failed.") {
          return NextResponse.json(
            { message: "Draft saved, but the featured image could not be attached. Please retry." },
            { status: 502, headers: { "Cache-Control": "no-store" } }
          );
        }
      }
    }

    return new NextResponse(payload || null, {
      status: upstream.status,
      headers: { "Content-Type": "application/json", "Cache-Control": "no-store" }
    });
  } catch {
    return NextResponse.json({ message: "Content service is temporarily unavailable." }, { status: 503 });
  }
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
