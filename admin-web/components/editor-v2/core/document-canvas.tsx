"use client";

import { useEffect, useState } from "react";

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
  const [inserterOpen, setInserterOpen] = useState(false);
  const [insertAfterBlockId, setInsertAfterBlockId] =
    useState<string | undefined>();

  useEffect(() => {
    if (!initialDocument) return;
    setDocument(initialDocument);
  }, [initialDocument]);

  function commit(nextDocument: CmsDocument) {
    setDocument(nextDocument);
    onChange?.(nextDocument);
  }

  function openInserter(afterBlockId?: string) {
    setInsertAfterBlockId(afterBlockId);
    setInserterOpen(true);
  }

  function insert(type: CmsBlockType) {
    commit(
      addBlock(
        document,
        createBlock(type),
        insertAfterBlockId,
      ),
    );

    setInserterOpen(false);
    setInsertAfterBlockId(undefined);
  }

  return (
    <section className="wp-editor-canvas">
      <header className="wp-editor-topbar">
        <div>
          <span className="section-kicker">VENUSREALM EDITOR</span>
          <strong>Visual content editor</strong>
        </div>

        <div className="wp-editor-topbar-actions">
          <span>{document.blocks.length} blocks</span>

          <button
            type="button"
            className="wp-add-block-button"
            disabled={disabled}
            onClick={() => openInserter()}
          >
            + Add block
          </button>
        </div>
      </header>

      <div className="wp-editor-paper">
        {document.blocks.length === 0 ? (
          <button
            type="button"
            className="wp-editor-empty"
            disabled={disabled}
            onClick={() => openInserter()}
          >
            <strong>Start writing</strong>
            <span>
              Add a paragraph, heading, image, table or another block.
            </span>
          </button>
        ) : (
          <div className="wp-editor-block-list">
            {document.blocks.map((block, index) => (
              <div
                className="wp-editor-block-row"
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
                    commit(
                      moveBlock(document, block.id, "up"),
                    )
                  }
                  onMoveDown={() =>
                    commit(
                      moveBlock(document, block.id, "down"),
                    )
                  }
                  onDuplicate={() =>
                    commit(
                      duplicateBlock(document, block.id),
                    )
                  }
                  onRemove={() =>
                    commit(
                      removeBlock(document, block.id),
                    )
                  }
                />

                <button
                  type="button"
                  className="wp-inline-add"
                  disabled={disabled}
                  aria-label={`Add block after ${block.type}`}
                  onClick={() => openInserter(block.id)}
                >
                  +
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <BlockInserter
        open={inserterOpen}
        disabled={disabled}
        onClose={() => {
          setInserterOpen(false);
          setInsertAfterBlockId(undefined);
        }}
        onInsert={insert}
      />
    </section>
  );
}
