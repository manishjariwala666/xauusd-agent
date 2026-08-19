"use client";

import type {
  CmsAccordionBlock,
} from "@/lib/editor-v2/document-types";

type Props = {
  block: CmsAccordionBlock;
  disabled?: boolean;
  onChange: (block: CmsAccordionBlock) => void;
};

export function AccordionBlockEditor({
  block,
  disabled = false,
  onChange,
}: Props) {
  function addItem() {
    onChange({
      ...block,
      items: [
        ...block.items,
        {
          id: `accordion-item-${crypto.randomUUID()}`,
          title: "New accordion item",
          html: "<p>Add accordion content here.</p>",
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
    <div className="editor-v2-accordion-editor">
      {block.items.map((item, index) => (
        <section
          className="editor-v2-accordion-item"
          key={item.id}
        >
          <header>
            <strong>Item {index + 1}</strong>

            <button
              type="button"
              className="danger-link"
              disabled={disabled || block.items.length === 1}
              onClick={() => removeItem(item.id)}
            >
              Remove
            </button>
          </header>

          <label>
            <span>Question / title</span>

            <input
              value={item.title}
              disabled={disabled}
              maxLength={240}
              onChange={event =>
                onChange({
                  ...block,
                  items: block.items.map(current =>
                    current.id === item.id
                      ? {
                          ...current,
                          title: event.target.value,
                        }
                      : current,
                  ),
                })
              }
            />
          </label>

          <label>
            <span>Answer / content</span>

            <textarea
              value={item.html}
              disabled={disabled}
              rows={5}
              onChange={event =>
                onChange({
                  ...block,
                  items: block.items.map(current =>
                    current.id === item.id
                      ? {
                          ...current,
                          html: event.target.value,
                        }
                      : current,
                  ),
                })
              }
            />
          </label>
        </section>
      ))}

      <button
        type="button"
        className="secondary-button"
        disabled={disabled}
        onClick={addItem}
      >
        + Add accordion item
      </button>
    </div>
  );
}
