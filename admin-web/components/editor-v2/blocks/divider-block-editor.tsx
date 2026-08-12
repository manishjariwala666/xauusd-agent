"use client";

import type { CmsDividerBlock } from "@/lib/editor-v2/document-types";

type Props = {
  block: CmsDividerBlock;
  disabled?: boolean;
  onChange: (block: CmsDividerBlock) => void;
};

export function DividerBlockEditor({
  block,
  disabled = false,
  onChange,
}: Props) {
  return (
    <div className="editor-v2-divider-editor">
      <label>
        <span>Divider style</span>

        <select
          value={block.style}
          disabled={disabled}
          onChange={event =>
            onChange({
              ...block,
              style: event.target.value as CmsDividerBlock["style"],
            })
          }
        >
          <option value="solid">Solid line</option>
          <option value="dashed">Dashed line</option>
          <option value="dots">Dotted line</option>
        </select>
      </label>

      <div className="editor-v2-divider-preview">
        <hr className={`divider-${block.style}`} />
      </div>
    </div>
  );
}
