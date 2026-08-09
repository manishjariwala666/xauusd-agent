import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import {
  normalizeMediaPayloadUrls,
  normalizeMediaUrl,
} from "../lib/media-url";

const root = resolve(import.meta.dirname, "..");
const source = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("Phase 3A Media Library", () => {
  it("rebases local media paths and blocks private production URLs", () => {
    const backend = "https://backend.example.com";
    const fallback = "https://admin.example.com/media-fallback.svg";

    expect(
      normalizeMediaUrl(
        "http://127.0.0.1:8000/media-local/uploads/chart.webp",
        backend,
        fallback,
      ),
    ).toBe("https://backend.example.com/media-local/uploads/chart.webp");
    expect(
      normalizeMediaUrl("file:///tmp/private.png", backend, fallback),
    ).toBe(fallback);
    expect(
      normalizeMediaPayloadUrls(
        {
          items: [
            {
              public_url: "http://localhost:8000/media-local/uploads/a.png",
              thumbnail_url: null,
            },
          ],
        },
        backend,
        fallback,
      ),
    ).toMatchObject({
      items: [
        {
          public_url: "https://backend.example.com/media-local/uploads/a.png",
          thumbnail_url: "https://backend.example.com/media-local/uploads/a.png",
        },
      ],
    });
  });

  it("provides the protected media route and real library controls", () => {
    expect(existsSync(resolve(root, "app/admin/(protected)/media/page.tsx"))).toBe(true);
    const library = source("components/media-library.tsx");
    const studioV2Library = source(
      "components/editor-v2/media/media-library-workspace.tsx",
    );
    for (const label of ["Upload Media", "Search filename", "Copy URL", "Edit image metadata", "Restore", "Delete permanently"]) expect(library).toContain(label);
    expect(library).toContain('type="file"');
    expect(library).toContain("window.confirm");
    expect(library).toContain("thumbnail_url");
    expect(library).toContain('loading="lazy"');
    expect(studioV2Library).toContain(
      'event.currentTarget.src = "/media-fallback.svg"',
    );
  });

  it("keeps upload and mutations behind session and CSRF BFF checks", () => {
    const proxy = source("app/api/admin/media/[...path]/route.ts");
    const featured = source("app/api/admin/featured-image/[contentId]/route.ts");
    expect(proxy).toContain("verifyCsrfToken");
    expect(proxy).toContain("ADMIN_SESSION_COOKIE");
    expect(proxy).toContain("arrayBuffer");
    expect(featured).toContain("verifyCsrfToken");
    expect(proxy + featured).not.toMatch(/SUPABASE|DATABASE_URL|service.role/i);
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
});
