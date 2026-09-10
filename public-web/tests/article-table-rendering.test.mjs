import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const source = readFileSync(new URL("../components/article-content.tsx", import.meta.url), "utf8");

test("public article renderer preserves CMS table structure", () => {
  assert.match(source, /parseHtmlTable/);
  assert.match(source, /@@VR_TABLE_/);
  assert.match(source, /block\.type === "table"/);
  assert.match(source, /<table/);
  assert.match(source, /<th/);
  assert.match(source, /<td/);
});

test("table cells are rendered as text instead of raw CMS HTML", () => {
  assert.match(source, /replace\(\/<\[\^>\]\+>\/g, " "\)/);
  assert.doesNotMatch(source, /dangerouslySetInnerHTML/);
});
