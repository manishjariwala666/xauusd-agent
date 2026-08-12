"use client";

import type { CmsHeadingBlock } from "@/lib/editor-v2/document-types";

type HeadingBlockEditorProps = {
  block: CmsHeadingBlock;
  disabled?: boolean;
  onChange: (block: CmsHeadingBlock) => void;
};

export function HeadingBlockEditor({
  block,
  disabled = false,
  onChange,
}: HeadingBlockEditorProps) {
  return (
    <div className="editor-v2-heading-editor">
      <label>
        <span>Heading level</span>
        <select
          value={block.level}
          disabled={disabled}
          onChange={event =>
            onChange({
              ...block,
              level: Number(event.target.value) as 1 | 2 | 3 | 4 | 5 | 6,
            })
          }
        >
          <option value={1}>Heading 1</option>
          <option value={2}>Heading 2</option>
          <option value={3}>Heading 3</option>
          <option value={4}>Heading 4</option>
          <option value={5}>Heading 5</option>
          <option value={6}>Heading 6</option>
        </select>
      </label>

      <label>
        <span>Heading text</span>
        <input
          value={block.text}
          disabled={disabled}
          onChange={event =>
            onChange({
              ...block,
              text: event.target.value,
            })
          }
          placeholder="Add section heading"
          maxLength={240}
        />
      </label>
    </div>
  );
}
