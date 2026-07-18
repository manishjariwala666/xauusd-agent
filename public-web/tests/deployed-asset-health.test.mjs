import assert from "node:assert/strict";
import test from "node:test";

import { extractReferencedAssets, verifyHomepageAssets } from "../lib/deployed-asset-health.mjs";

const homepage = `<!doctype html><html><head>
  <link rel="stylesheet" href="/_next/static/chunks/site.css">
  <script src="/_next/static/chunks/app.js"></script>
  <script src="/_next/static/chunks/app.js"></script>
</head><body></body></html>`;

test("extracts and de-duplicates referenced CSS and JavaScript assets", () => {
  assert.deepEqual(extractReferencedAssets(homepage, "https://site.example/"), [
    "https://site.example/_next/static/chunks/site.css",
    "https://site.example/_next/static/chunks/app.js",
  ]);
});

test("passes only when every referenced homepage asset returns 200", async () => {
  const calls = [];
  const result = await verifyHomepageAssets({
    baseUrl: "https://site.example",
    fetchImplementation: async (url) => {
      calls.push(url);
      return url === "https://site.example/"
        ? new Response(homepage, { status: 200 })
        : new Response("asset", { status: 200 });
    },
  });

  assert.equal(result.homepageStatus, 200);
  assert.equal(result.assets.length, 2);
  assert.equal(calls.length, 3);
});

test("fails when any referenced asset is missing", async () => {
  await assert.rejects(
    verifyHomepageAssets({
      baseUrl: "https://site.example",
      fetchImplementation: async (url) => {
        if (url === "https://site.example/") return new Response(homepage, { status: 200 });
        return new Response("missing", { status: url.endsWith("site.css") ? 404 : 200 });
      },
    }),
    /site\.css: 404/,
  );
});

test("fails when the homepage has no deploy assets", async () => {
  await assert.rejects(
    verifyHomepageAssets({
      baseUrl: "https://site.example",
      fetchImplementation: async () => new Response("<html></html>", { status: 200 }),
    }),
    /did not reference any CSS or JavaScript assets/,
  );
});
