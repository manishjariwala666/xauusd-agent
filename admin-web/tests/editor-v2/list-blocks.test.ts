import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { createBlock } from "../../lib/editor-v2/block-factory";
import {
  cmsApiDetailToDocument,
  cmsDocumentToHtml,
} from "../../lib/editor-v2/converters";
import { createEmptyDocument } from "../../lib/editor-v2/document-store";
import type {
  CmsListBlock,
} from "../../lib/editor-v2/document-types";

const adminRoot = resolve(import.meta.dirname, "../..");

describe("Studio V2 list blocks", () => {
  it("creates bullet and numbered list blocks through the shared factory", () => {
    const bullet = createBlock("bullet-list") as CmsListBlock;
    const numbered = createBlock("numbered-list") as CmsListBlock;

    expect(bullet).toMatchObject({
      type: "bullet-list",
      items: [{ text: "" }],
    });
    expect(numbered).toMatchObject({
      type: "numbered-list",
      items: [{ text: "" }],
    });
  });

  it("serializes and restores both list types in the existing document JSON", () => {
    const document = createEmptyDocument();
    document.blocks = [
      {
        id: "bullet-list-1",
        type: "bullet-list",
        items: [
          { id: "bullet-1", text: "Gold & silver" },
          { id: "bullet-2", text: "Risk < reward" },
        ],
      },
      {
        id: "numbered-list-1",
        type: "numbered-list",
        items: [
          { id: "numbered-1", text: "Plan" },
          { id: "numbered-2", text: "Review" },
        ],
      },
    ];

    const html = cmsDocumentToHtml(document);

    expect(html).toContain(
      "<ul><li>Gold &amp; silver</li><li>Risk &lt; reward</li></ul>",
    );
    expect(html).toContain(
      "<ol><li>Plan</li><li>Review</li></ol>",
    );

    const restored = cmsApiDetailToDocument({ id: 79, body: html });
    expect(restored.blocks).toEqual(document.blocks);
  });

  it("registers both blocks in the existing picker and shared renderer", () => {
    const picker = readFileSync(
      resolve(
        adminRoot,
        "components/editor-v2/blocks/block-inserter.tsx",
      ),
      "utf8",
    );
    const renderer = readFileSync(
      resolve(
        adminRoot,
        "components/editor-v2/blocks/block-renderer.tsx",
      ),
      "utf8",
    );
    const editor = readFileSync(
      resolve(
        adminRoot,
        "components/editor-v2/blocks/list-block-editor.tsx",
      ),
      "utf8",
    );

    expect(picker).toContain('label: "Bullet List"');
    expect(picker).toContain('label: "Numbered List"');
    expect(renderer).toContain('case "bullet-list"');
    expect(renderer).toContain('case "numbered-list"');
    expect(editor).toContain("function addItem()");
    expect(editor).toContain("function removeItem(itemId: string)");
  });
});
