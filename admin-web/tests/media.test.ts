import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import {
  normalizeMediaPayloadUrls,
  normalizeMediaUrl,
} from "../lib/media-url";
import { readMediaResponse } from "../lib/media-response";
import {
  MEDIA_PROXY_SAFE_UPLOAD_BYTES,
  prepareMediaUpload,
} from "../lib/media-upload";

const root = resolve(import.meta.dirname, "..");
const source = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("Phase 3A Media Library", () => {
  it("maps private media records to unique authenticated BFF URLs", () => {
    const backend = "https://backend.example.com";
    const fallback = "https://admin.example.com/media-fallback.svg";

    expect(
      normalizeMediaUrl("file:///tmp/private.png", backend, fallback),
    ).toBe(fallback);
    expect(
      normalizeMediaPayloadUrls(
        {
          items: [
            {
              id: 101,
              public_url: "http://localhost:8000/media-local/uploads/a.png",
              thumbnail_url: null,
            },
            {
              id: 102,
              public_url: "http://127.0.0.1:8000/media-local/uploads/b.png",
              thumbnail_url: "http://127.0.0.1:8000/media-local/thumbnails/b.webp",
            },
          ],
        },
        backend,
        fallback,
      ),
    ).toMatchObject({
      items: [
        {
          public_url: "https://admin.example.com/api/admin/media-file/101?variant=original",
          thumbnail_url: "https://admin.example.com/api/admin/media-file/101?variant=thumbnail",
        },
        {
          public_url: "https://admin.example.com/api/admin/media-file/102?variant=original",
          thumbnail_url: "https://admin.example.com/api/admin/media-file/102?variant=thumbnail",
        },
      ],
    });
  });

  it("streams durable HTTPS media through the authenticated BFF", () => {
    const result = normalizeMediaPayloadUrls(
      {
        id: 103,
        public_url: "https://storage.example.invalid/admin-media/one.png",
        thumbnail_url: "https://storage.example.invalid/admin-media/one.webp",
      },
      "https://backend.example.com",
      "https://admin.example.com/media-fallback.svg",
    );

    expect(result).toMatchObject({
      public_url: "https://admin.example.com/api/admin/media-file/103?variant=original",
      thumbnail_url: "https://admin.example.com/api/admin/media-file/103?variant=thumbnail",
    });
  });

  it("provides the protected media route and real library controls", () => {
    expect(existsSync(resolve(root, "app/admin/(protected)/media/page.tsx"))).toBe(true);
    const library = source("components/media-library.tsx");
    const studioV2Library = source(
      "components/editor-v2/media/media-library-workspace.tsx",
    );
    const studioV2Gallery = source(
      "components/editor-v2/gallery/gallery-manager-workspace.tsx",
    );
    for (const label of ["Upload Media", "Search filename", "Copy URL", "Edit image metadata", "Restore", "Delete permanently"]) expect(library).toContain(label);
    expect(library).toContain('type="file"');
    expect(library).toContain("window.confirm");
    expect(library).toContain("thumbnail_url");
    expect(library).toContain('loading="lazy"');
    expect(studioV2Library).toContain(
      'event.currentTarget.src = "/media-fallback.svg"',
    );
    const mediaListRoute = source("app/api/admin/media/route.ts");
    expect(mediaListRoute).toContain("normalizeMediaPayloadUrls");
    expect(mediaListRoute).toContain("request.nextUrl.origin");
    expect(mediaListRoute).not.toContain("127.0.0.1");
    expect(studioV2Library).toContain("/api/admin/media?");
    expect(studioV2Gallery).toContain("/api/admin/media?");
    expect(studioV2Gallery).toContain("thumbnail_url");
  });

  it("keeps upload and mutations behind session and CSRF BFF checks", () => {
    const proxy = source("app/api/admin/media/[...path]/route.ts");
    const featured = source("app/api/admin/featured-image/[contentId]/route.ts");
    expect(proxy).toContain("verifyCsrfToken");
    expect(proxy).toContain("ADMIN_SESSION_COOKIE");
    expect(proxy).toContain("arrayBuffer");
    expect(featured).toContain("verifyCsrfToken");
    expect(proxy + featured).not.toMatch(/SUPABASE|DATABASE_URL|service.role/i);
    const fileProxy = source("app/api/admin/media-file/[mediaId]/route.ts");
    expect(fileProxy).toContain("ADMIN_SESSION_COOKIE");
    expect(fileProxy).toContain("X-Admin-BFF-Key");
    expect(fileProxy).toContain("X-Content-Type-Options");
  });

  it("replaces the placeholder with a functional featured-image picker", () => {
    const editor = source("components/content-editor.tsx");
    const picker = source("components/featured-image-picker.tsx");
    expect(editor).toContain("FeaturedImagePicker");
    for (const label of ["Choose from library", "Upload new", "Replace", "Remove", "Save alt text"]) expect(picker).toContain(label);
    expect(picker).toContain("/api/admin/featured-image/");
    expect(picker).not.toContain("AI image");
  });

  it("stays responsive and dependency-light", () => {
    const css = source("app/globals.css");
    const pkg = source("package.json");
    expect(css).toContain(".media-collection.grid");
    expect(css).toContain("@media (max-width: 720px)");
    expect(css).toMatch(/overflow-x:\s*hidden/);
    expect(pkg).not.toMatch(/lightbox|dropzone|gallery|framer-motion/);
  });

  it("reports non-JSON upload failures without hiding the HTTP status", async () => {
    await expect(
      readMediaResponse(
        new Response("upstream gateway error", { status: 502 }),
      ),
    ).rejects.toThrow("invalid response (HTTP 502)");

    await expect(
      readMediaResponse(
        new Response(JSON.stringify({ id: 7 }), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    ).resolves.toEqual({ id: 7 });
  });

  it("keeps small uploads intact and rejects oversized GIFs safely", async () => {
    const smallImage = new File([new Uint8Array(16)], "chart.png", {
      type: "image/png",
    });
    await expect(prepareMediaUpload(smallImage)).resolves.toBe(smallImage);

    const largeGif = new File(
      [new Uint8Array(MEDIA_PROXY_SAFE_UPLOAD_BYTES + 1)],
      "animated.gif",
      { type: "image/gif" },
    );
    await expect(prepareMediaUpload(largeGif)).rejects.toThrow(
      "GIF images must be 3 MB or smaller.",
    );
  });

  it("optimizes oversized non-GIF images before the Netlify proxy", () => {
    const helper = source("lib/media-upload.ts");
    const workspace = source(
      "components/editor-v2/media/media-library-workspace.tsx",
    );
    const dialog = source("components/media-library-dialog.tsx");

    expect(helper).toContain('"image/webp"');
    expect(helper).toContain("createImageBitmap");
    expect(workspace).toContain("prepareMediaUpload(file)");
    expect(dialog).toContain("prepareMediaUpload(uploadFile)");
  });
});
