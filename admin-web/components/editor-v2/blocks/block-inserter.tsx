"use client";

import type { CmsBlockType } from "@/lib/editor-v2/document-types";

type BlockInserterProps = {
  disabled?: boolean;
  onInsert: (type: CmsBlockType) => void;
};

const options: Array<{
  type: CmsBlockType;
  label: string;
  description: string;
}> = [
  { type: "paragraph", label: "Paragraph", description: "Normal text block" },
  { type: "heading", label: "Heading", description: "H1 to H6 heading" },
  { type: "image", label: "Image", description: "Single media image" },
  { type: "gallery", label: "Gallery", description: "Responsive image gallery" },
  { type: "table", label: "Table", description: "Structured data table" },
  { type: "quote", label: "Quote", description: "Quotation and citation" },
  { type: "code", label: "Code", description: "Code snippet block" },
  { type: "button", label: "Button", description: "Call-to-action button" },
  { type: "divider", label: "Divider", description: "Section separator" },
  { type: "accordion", label: "Accordion", description: "Expandable content" },
  { type: "youtube", label: "YouTube", description: "Video embed" },
];

export function BlockInserter({
  disabled = false,
  onInsert,
}: BlockInserterProps) {
  return (
    <section className="editor-v2-block-inserter">
      <header>
        <strong>Add block</strong>
        <span>Choose content type</span>
      </header>

      <div className="editor-v2-block-grid">
        {options.map(option => (
          <button
            key={option.type}
            type="button"
            disabled={disabled}
            onClick={() => onInsert(option.type)}
          >
            <strong>{option.label}</strong>
            <small>{option.description}</small>
          </button>
        ))}
      </div>
    </section>
  );
}
