import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { normalizeMediaPayloadUrls, normalizeMediaUrl } from "../lib/media-url";
import { readMediaResponse } from "../lib/media-response";
import { MEDIA_PROXY_SAFE_UPLOAD_BYTES, prepareMediaUpload } from "../lib/media-upload";

const root = resolve(import.meta.dirname, "..");
const source = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("Phase 3A Media Library", () => {
  it("normalizes absolute, private and relative media URLs safely", () => {
    const backend = "https://backend.example.com";
    const fallback = "https://admin.example.com/media-fallback.svg";
    expect(normalizeMediaUrl("https://cdn.example.com/a.png", backend, fallback)).toBe("https://cdn.example.com/a.png");
    expect(normalizeMediaUrl("http://localhost:8000/a.png", backend, fallback)).toBe(fallback);
    expect(normalizeMediaUrl("http://127.0.0.1:8000/a.png", backend, fallback)).toBe(fallback);
    expect(normalizeMediaUrl("/media/a.png", backend, fallback)).toBe("https://backend.example.com/media/a.png");
    expect(normalizeMediaUrl("file:///tmp/private.png", backend, fallback)).toBe(fallback);
  });

  it("maps media records to canonical same-origin original and thumbnail BFF URLs", () => {
    const result = normalizeMediaPayloadUrls({
      items: [{ id: 101, public_url: "http://localhost:8000/a.png", thumbnail_url: null }],
    }, "https://backend.example.com", "https://admin.example.com/media-fallback.svg");
    expect(result).toMatchObject({ items: [{
      public_url: "/api/admin/media-file/101?variant=original",
      thumbnail_url: "/api/admin/media-file/101?variant=thumbnail",
    }] });
  });

  it("streams durable HTTPS media through the same-origin authenticated BFF", () => {
    const result = normalizeMediaPayloadUrls({ id: 103, public_url: "https://storage.example.invalid/admin-media/one.png", thumbnail_url: "https://storage.example.invalid/admin-media/one.webp" }, "https://backend.example.com", "https://admin.example.com/media-fallback.svg");
    expect(result).toMatchObject({ public_url: "/api/admin/media-file/103?variant=original", thumbnail_url: "/api/admin/media-file/103?variant=thumbnail" });
  });

  it("normalizes successful upload responses before picker selection", () => {
    const proxy = source("app/api/admin/media/[...path]/route.ts");
    expect(proxy).toContain("if (upstream.ok && payload)");
    expect(proxy).toContain("normalizeMediaPayloadUrls");
    expect(proxy).not.toContain('request.method === "GET" && upstream.ok');
    const dialog = source("components/media-library-dialog.tsx");
    expect(dialog).toContain("normalizeMediaLibraryAsset");
    expect(dialog).toContain("onSelect(asset)");
    expect(dialog).toContain("const id = Number(candidate.id)");
    expect(dialog).toContain("thumbnail_url || item.public_url");
  });

  it("keeps Studio V2 picker selection and reload on canonical media IDs", () => {
    const insights = source("components/editor-v2/seo/content-insights-panel.tsx");
    const workspace = source("components/editor-v2/core/studio-workspace.tsx");
    expect(insights).toContain("onChange(asset.id, asset)");
    expect(insights).toContain("/api/admin/media/${document.featuredMediaId}");
    expect(insights).toContain("selectedAsset?.thumbnail_url");
    expect(workspace).toContain("featuredMediaId: mediaId");
  });

  it("uses canonical gallery URLs with a visible broken-image fallback", () => {
    const gallery = source("components/editor-v2/gallery/gallery-manager-workspace.tsx");
    expect(gallery).toContain("/api/admin/media?");
    expect(gallery).toContain("item.thumbnail_url || item.public_url");
    expect(gallery).toContain('event.currentTarget.src = "/media-fallback.svg"');
    expect(gallery).toContain("fallbackApplied");
  });

  it("falls thumbnail byte requests back to the original image", () => {
    const fileProxy = source("app/api/admin/media-file/[mediaId]/route.ts");
    expect(fileProxy).toContain('["thumbnail", "original"]');
    expect(fileProxy).toContain('variant === "thumbnail" && upstream.status === 404');
    expect(fileProxy).toContain("ADMIN_SESSION_COOKIE");
    expect(fileProxy).toContain("X-Admin-BFF-Key");
  });

  it("provides the protected media route and real library controls", () => {
    expect(existsSync(resolve(root, "app/admin/(protected)/media/page.tsx"))).toBe(true);
    const library = source("components/media-library.tsx");
    const studioV2Library = source("components/editor-v2/media/media-library-workspace.tsx");
    for (const label of ["Upload Media", "Search filename", "Copy URL", "Edit image metadata", "Restore", "Delete permanently"]) expect(library).toContain(label);
    expect(library).toContain('type="file"');
    expect(library).toContain("window.confirm");
    expect(studioV2Library).toContain('event.currentTarget.src = "/media-fallback.svg"');
  });

  it("keeps upload and mutations behind session and CSRF BFF checks", () => {
    const proxy = source("app/api/admin/media/[...path]/route.ts");
    expect(proxy).toContain("verifyCsrfToken");
    expect(proxy).toContain("ADMIN_SESSION_COOKIE");
    expect(proxy).toContain("arrayBuffer");
    expect(proxy).not.toMatch(/SUPABASE|DATABASE_URL|service.role/i);
  });

  it("reports non-JSON upload failures without hiding the HTTP status", async () => {
    await expect(readMediaResponse(new Response("upstream gateway error", { status: 502 }))).rejects.toThrow("invalid response (HTTP 502)");
    await expect(readMediaResponse(new Response(JSON.stringify({ id: 7 }), { status: 201, headers: { "Content-Type": "application/json" } }))).resolves.toEqual({ id: 7 });
  });

  it("keeps small uploads intact and rejects oversized GIFs safely", async () => {
    const smallImage = new File([new Uint8Array(16)], "chart.png", { type: "image/png" });
    await expect(prepareMediaUpload(smallImage)).resolves.toBe(smallImage);
    const largeGif = new File([new Uint8Array(MEDIA_PROXY_SAFE_UPLOAD_BYTES + 1)], "animated.gif", { type: "image/gif" });
    await expect(prepareMediaUpload(largeGif)).rejects.toThrow("GIF images must be 3 MB or smaller.");
  });

  it("optimizes oversized non-GIF images before the proxy", () => {
    const helper = source("lib/media-upload.ts");
    const workspace = source("components/editor-v2/media/media-library-workspace.tsx");
    const dialog = source("components/media-library-dialog.tsx");
    expect(helper).toContain('"image/webp"');
    expect(helper).toContain("createImageBitmap");
    expect(workspace).toContain("prepareMediaUpload(file)");
    expect(dialog).toContain("prepareMediaUpload(uploadFile)");
  });
});
