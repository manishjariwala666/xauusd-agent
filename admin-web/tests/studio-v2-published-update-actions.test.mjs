import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const actionsSource = readFileSync(
  new URL("../components/editor-v2/core/published-post-actions.tsx", import.meta.url),
  "utf8",
);
const pageSource = readFileSync(
  new URL("../app/studio-v2/page.tsx", import.meta.url),
  "utf8",
);

test("published Studio V2 posts can be updated without reverting to draft", () => {
  assert.match(actionsSource, /method:\s*"PATCH"/);
  assert.match(actionsSource, /status:\s*"published"/);
  assert.match(actionsSource, /published_at:\s*document\.publishedAt/);
  assert.match(actionsSource, /Update Published Post/);
});

test("published Studio V2 posts expose a direct public view link", () => {
  assert.match(actionsSource, /https:\/\/venusrealm\.net\/blog\//);
  assert.match(actionsSource, /View Post ↗/);
});

test("Studio V2 renders published update actions", () => {
  assert.match(pageSource, /PublishedPostActions/);
  assert.match(pageSource, /<PublishedPostActions \/>/);
});
