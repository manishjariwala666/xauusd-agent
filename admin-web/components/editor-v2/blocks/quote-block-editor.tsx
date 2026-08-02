"use client";

import type { CmsQuoteBlock } from "@/lib/editor-v2/document-types";
import { BlockRichTextEditor } from "../core/block-rich-text-editor";

type Props = {
  block: CmsQuoteBlock;
  disabled?: boolean;
  onChange: (block: CmsQuoteBlock) => void;
};

export function QuoteBlockEditor({
  block,
  disabled = false,
  onChange,
}: Props) {
  return (
    <div className="editor-v2-quote-editor">
      <BlockRichTextEditor
        value={block.html}
        disabled={disabled}
        placeholder="Write quotation…"
        onChange={html => onChange({ ...block, html })}
      />

      <label>
        <span>Citation / source</span>
        <input
          value={block.citation}
          disabled={disabled}
          maxLength={240}
          placeholder="Author, publication or source"
          onChange={event =>
            onChange({
              ...block,
              citation: event.target.value,
            })
          }
        />
      </label>
    </div>
  );
}
