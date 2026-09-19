import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (relative) => fs.readFileSync(path.join(root, relative), "utf8");

test("homepage section anchors match footer and jump navigation targets", () => {
  const page = read("app/page.tsx");

  for (const id of ["overview", "how-it-works", "research", "membership", "faq"]) {
    assert.match(page, new RegExp(`id=["']${id}["']`));
  }

  assert.match(page, /href="#overview"/);
  assert.match(page, /href="#how-it-works"/);
  assert.match(page, /href="#research"/);
  assert.match(page, /href="#membership"/);
  assert.match(page, /href="#faq"/);
});

test("homepage exposes a clear member onboarding path without public signal detail", () => {
  const page = read("app/page.tsx");

  assert.match(page, /href="\/signup"/);
  assert.match(page, /href="\/login"/);
  assert.match(page, /Complete paid-access verification/);
  assert.match(page, /Live direction, entry, stop-loss and targets stay out of the public homepage/);
});

test("mobile header labels authenticated access as Member Desk", () => {
  const header = read("components/site-header.tsx");
  const mobile = read("components/mobile-nav.tsx");

  assert.match(header, /accessLabel={hasMemberSession \? "Member Desk" : "Member Access"}/);
  assert.match(mobile, />{accessLabel}<\/a>/);
});
