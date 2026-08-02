"use client";

import { useState } from "react";

import { createBlock } from "@/lib/editor-v2/block-factory";
import {
  addBlock,
  createEmptyDocument,
  duplicateBlock,
  moveBlock,
  removeBlock,
  updateBlock,
} from "@/lib/editor-v2/document-store";
import type {
  CmsBlockType,
  CmsDocument,
} from "@/lib/editor-v2/document-types";

import { BlockInserter } from "../blocks/block-inserter";
import { BlockRenderer } from "../blocks/block-renderer";
import { InlineBlockInserter } from "../blocks/inline-block-inserter";

type DocumentCanvasProps = {
  initialDocument?: CmsDocument;
  disabled?: boolean;
  onChange?: (document: CmsDocument) => void;
};

export function DocumentCanvas({
  initialDocument,
  disabled = false,
  onChange,
}: DocumentCanvasProps) {
  const [document, setDocument] = useState<CmsDocument>(
    initialDocument ?? createEmptyDocument(),
  );

  function commit(nextDocument: CmsDocument) {
    setDocument(nextDocument);
    onChange?.(nextDocument);
  }

  function insert(
    type: CmsBlockType,
    afterBlockId?: string,
  ) {
    commit(
      addBlock(
        document,
        createBlock(type),
        afterBlockId,
      ),
    );
  }

  return (
    <section className="editor-v2-document-canvas">
      <header className="editor-v2-canvas-header">
        <div>
          <span className="section-kicker">CUSTOM CMS V2</span>
          <h2>Content blocks</h2>
          <p>Add, arrange and configure reusable content blocks.</p>
        </div>

        <div className="editor-v2-canvas-stats">
          <strong>{document.blocks.length}</strong>
          <span>blocks</span>
        </div>
      </header>

      <div className="editor-v2-block-list">
        {document.blocks.map((block, index) => (
          <div
            className="editor-v2-block-with-inserter"
            key={block.id}
          >
            <BlockRenderer
              block={block}
              index={index}
              total={document.blocks.length}
              disabled={disabled}
            onChange={nextBlock =>
              commit(
                updateBlock(
                  document,
                  block.id,
                  () => nextBlock,
                ),
              )
            }
            onMoveUp={() =>
              commit(moveBlock(document, block.id, "up"))
            }
            onMoveDown={() =>
              commit(moveBlock(document, block.id, "down"))
            }
            onDuplicate={() =>
              commit(duplicateBlock(document, block.id))
            }
              onRemove={() =>
                commit(removeBlock(document, block.id))
              }
            />

            <InlineBlockInserter
              afterBlockId={block.id}
              disabled={disabled}
              onInsert={insert}
            />
          </div>
        ))}
      </div>

      <BlockInserter
        disabled={disabled}
        onInsert={insert}
      />
    </section>
  );
}
