"use client";

import { useState } from "react";

import type {
  CmsBlockType,
} from "@/lib/editor-v2/document-types";

type InlineBlockInserterProps = {
  afterBlockId: string;
  disabled?: boolean;
  onInsert: (
    type: CmsBlockType,
    afterBlockId: string,
  ) => void;
};

const quickBlocks: Array<{
  type: CmsBlockType;
  label: string;
}> = [
  { type: "paragraph", label: "Paragraph" },
  { type: "heading", label: "Heading" },
  { type: "image", label: "Image" },
  { type: "gallery", label: "Gallery" },
  { type: "table", label: "Table" },
  { type: "bullet-list", label: "Bullet List" },
  { type: "numbered-list", label: "Numbered List" },
  { type: "quote", label: "Quote" },
  { type: "button", label: "Button" },
  { type: "accordion", label: "Accordion" },
  { type: "youtube", label: "YouTube" },
];

export function InlineBlockInserter({
  afterBlockId,
  disabled = false,
  onInsert,
}: InlineBlockInserterProps) {
  const [open, setOpen] = useState(false);

  function insert(type: CmsBlockType) {
    onInsert(type, afterBlockId);
    setOpen(false);
  }

  return (
    <div className="editor-v2-inline-inserter">
      <button
        type="button"
        className="editor-v2-inline-add"
        disabled={disabled}
        onClick={() => setOpen(value => !value)}
        aria-expanded={open}
      >
        + Add block here
      </button>

      {open ? (
        <div
          className="editor-v2-inline-menu"
          role="menu"
          aria-label="Insert content block"
        >
          {quickBlocks.map(option => (
            <button
              key={option.type}
              type="button"
              role="menuitem"
              onClick={() => insert(option.type)}
            >
              {option.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
