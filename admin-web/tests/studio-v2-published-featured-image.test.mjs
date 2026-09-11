import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const syncSource = readFileSync(new URL("../components/editor-v2/core/published-featured-image-sync.tsx", import.meta.url), "utf8");
const pageSource = readFileSync(new URL("../app/studio-v2/page.tsx", import.meta.url), "utf8");

test("persisted Studio V2 documents sync featured images through protected admin route", () => {
  assert.doesNotMatch(syncSource, /document\.status !== "published"/);
  assert.match(syncSource, /const contentId = Number\(document\.id \|\| 0\)/);
  assert.match(syncSource, /\/api\/admin\/featured-image\/\$\{contentId\}/);
  assert.match(syncSource, /method: mediaId \? "POST" : "DELETE"/);
  assert.match(syncSource, /JSON\.stringify\(\{ media_id: mediaId \}\)/);
});

test("Studio V2 activates featured image sync", () => {
  assert.match(pageSource, /PublishedFeaturedImageSync/);
  assert.match(pageSource, /<PublishedFeaturedImageSync \/>/);
});
