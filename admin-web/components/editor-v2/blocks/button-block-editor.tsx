"use client";

import type { CmsButtonBlock } from "@/lib/editor-v2/document-types";

type Props = {
  block: CmsButtonBlock;
  disabled?: boolean;
  onChange: (block: CmsButtonBlock) => void;
};

export function ButtonBlockEditor({
  block,
  disabled = false,
  onChange,
}: Props) {
  return (
    <div className="editor-v2-button-editor">
      <div className="editor-v2-button-fields">
        <label>
          <span>Button label</span>
          <input
            value={block.label}
            disabled={disabled}
            maxLength={100}
            onChange={event =>
              onChange({ ...block, label: event.target.value })
            }
          />
        </label>

        <label>
          <span>Destination URL</span>
          <input
            value={block.url}
            disabled={disabled}
            placeholder="https://example.com"
            onChange={event =>
              onChange({ ...block, url: event.target.value })
            }
          />
        </label>

        <label>
          <span>Style</span>
          <select
            value={block.style}
            disabled={disabled}
            onChange={event =>
              onChange({
                ...block,
                style: event.target.value as CmsButtonBlock["style"],
              })
            }
          >
            <option value="primary">Primary</option>
            <option value="secondary">Secondary</option>
            <option value="outline">Outline</option>
          </select>
        </label>

        <label>
          <span>Alignment</span>
          <select
            value={block.alignment}
            disabled={disabled}
            onChange={event =>
              onChange({
                ...block,
                alignment:
                  event.target.value as CmsButtonBlock["alignment"],
              })
            }
          >
            <option value="left">Left</option>
            <option value="center">Center</option>
            <option value="right">Right</option>
          </select>
        </label>
      </div>

      <div className={`editor-v2-button-preview align-${block.alignment}`}>
        <a
          href={block.url || "#"}
          className={`cms-button-${block.style}`}
          onClick={event => event.preventDefault()}
        >
          {block.label || "Button"}
        </a>
      </div>
    </div>
  );
}
