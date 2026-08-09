"use client";

import type { CmsListBlock } from "@/lib/editor-v2/document-types";

type Props = {
  block: CmsListBlock;
  disabled?: boolean;
  onChange: (block: CmsListBlock) => void;
};

export function ListBlockEditor({
  block,
  disabled = false,
  onChange,
}: Props) {
  const listLabel = block.type === "bullet-list"
    ? "bullet"
    : "numbered";

  function addItem() {
    onChange({
      ...block,
      items: [
        ...block.items,
        {
          id: `list-item-${crypto.randomUUID()}`,
          text: "",
        },
      ],
    });
  }

  function removeItem(itemId: string) {
    onChange({
      ...block,
      items: block.items.filter(item => item.id !== itemId),
    });
  }

  return (
    <div className="editor-v2-list-editor">
      {block.items.map((item, index) => (
        <div className="editor-v2-list-item" key={item.id}>
          <span aria-hidden="true">
            {block.type === "bullet-list" ? "•" : `${index + 1}.`}
          </span>

          <label>
            <span className="sr-only">
              {listLabel} list item {index + 1}
            </span>
            <input
              value={item.text}
              disabled={disabled}
              placeholder={`List item ${index + 1}`}
              onChange={event =>
                onChange({
                  ...block,
                  items: block.items.map(current =>
                    current.id === item.id
                      ? { ...current, text: event.target.value }
                      : current,
                  ),
                })
              }
            />
          </label>

          <button
            type="button"
            className="danger-link"
            disabled={disabled || block.items.length === 1}
            onClick={() => removeItem(item.id)}
            aria-label={`Remove list item ${index + 1}`}
          >
            Remove
          </button>
        </div>
      ))}

      <button
        type="button"
        className="secondary-button"
        disabled={disabled}
        onClick={addItem}
      >
        + Add list item
      </button>
    </div>
  );
}
