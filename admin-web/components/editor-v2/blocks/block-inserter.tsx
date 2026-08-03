"use client";

import { useMemo, useState } from "react";

import type {
  CmsBlockType,
} from "@/lib/editor-v2/document-types";

type BlockInserterProps = {
  open: boolean;
  disabled?: boolean;
  onClose: () => void;
  onInsert: (type: CmsBlockType) => void;
};

const options: Array<{
  type: CmsBlockType;
  icon: string;
  label: string;
  description: string;
}> = [
  {
    type: "paragraph",
    icon: "¶",
    label: "Paragraph",
    description: "Normal article text",
  },
  {
    type: "heading",
    icon: "H",
    label: "Heading",
    description: "Section heading",
  },
  {
    type: "image",
    icon: "▧",
    label: "Image",
    description: "Media Library image",
  },
  {
    type: "gallery",
    icon: "▦",
    label: "Gallery",
    description: "Responsive image gallery",
  },
  {
    type: "table",
    icon: "▤",
    label: "Table",
    description: "Rows and columns",
  },
  {
    type: "quote",
    icon: "❝",
    label: "Quote",
    description: "Quote and citation",
  },
  {
    type: "accordion",
    icon: "⌄",
    label: "FAQ / Accordion",
    description: "Expandable questions",
  },
  {
    type: "youtube",
    icon: "▶",
    label: "YouTube",
    description: "Video embed",
  },
  {
    type: "button",
    icon: "▣",
    label: "Button",
    description: "Call-to-action link",
  },
  {
    type: "divider",
    icon: "—",
    label: "Divider",
    description: "Section separator",
  },
  {
    type: "code",
    icon: "</>",
    label: "Code",
    description: "Formatted code snippet",
  },
];

export function BlockInserter({
  open,
  disabled = false,
  onClose,
  onInsert,
}: BlockInserterProps) {
  const [query, setQuery] = useState("");

  const filteredOptions = useMemo(() => {
    const normalized = query.trim().toLowerCase();

    if (!normalized) return options;

    return options.filter(option =>
      `${option.label} ${option.description}`
        .toLowerCase()
        .includes(normalized),
    );
  }, [query]);

  if (!open) return null;

  return (
    <div
      className="wp-block-picker-backdrop"
      role="presentation"
      onMouseDown={event => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <section
        className="wp-block-picker"
        role="dialog"
        aria-modal="true"
        aria-label="Add content block"
      >
        <header>
          <div>
            <strong>Add a block</strong>
            <span>Choose what you want to add</span>
          </div>

          <button
            type="button"
            className="wp-picker-close"
            onClick={onClose}
            aria-label="Close block picker"
          >
            ×
          </button>
        </header>

        <input
          autoFocus
          type="search"
          value={query}
          placeholder="Search blocks…"
          onChange={event => setQuery(event.target.value)}
        />

        <div className="wp-block-picker-grid">
          {filteredOptions.map(option => (
            <button
              key={option.type}
              type="button"
              disabled={disabled}
              onClick={() => {
                onInsert(option.type);
                setQuery("");
              }}
            >
              <span className="wp-block-icon">
                {option.icon}
              </span>

              <span>
                <strong>{option.label}</strong>
                <small>{option.description}</small>
              </span>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
