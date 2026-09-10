import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const source = readFileSync(new URL("../components/editor-v2/core/studio-workspace.tsx", import.meta.url), "utf8");

test("published Studio V2 posts can update featured image without reverting to draft", () => {
  assert.match(source, /syncPublishedFeaturedImage/);
  assert.match(source, /\/api\/admin\/featured-image\/\$\{document\.id\}/);
  assert.match(source, /method:\s*mediaId\s*\?\s*"POST"\s*:\s*"DELETE"/);
  assert.match(source, /document\.status === "published"/);
});
