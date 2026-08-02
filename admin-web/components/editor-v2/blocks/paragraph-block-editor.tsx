"use client";

import type {
  CmsParagraphBlock,
} from "@/lib/editor-v2/document-types";

import {
  BlockRichTextEditor,
} from "../core/block-rich-text-editor";

type ParagraphBlockEditorProps = {
  block: CmsParagraphBlock;
  disabled?: boolean;
  onChange: (block: CmsParagraphBlock) => void;
};

export function ParagraphBlockEditor({
  block,
  disabled = false,
  onChange,
}: ParagraphBlockEditorProps) {
  return (
    <div className="editor-v2-paragraph-editor">
      <BlockRichTextEditor
        value={block.html}
        disabled={disabled}
        placeholder="Write paragraph content…"
        onChange={html =>
          onChange({
            ...block,
            html,
          })
        }
      />
    </div>
  );
}
