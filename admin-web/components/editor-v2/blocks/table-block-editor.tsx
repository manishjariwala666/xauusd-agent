"use client";

import type { CmsTableBlock } from "@/lib/editor-v2/document-types";

type Props = {
  block: CmsTableBlock;
  disabled?: boolean;
  onChange: (block: CmsTableBlock) => void;
};

function createTable(rows: number, columns: number): string {
  const header = Array.from(
    { length: columns },
    (_, index) => `<th>Column ${index + 1}</th>`,
  ).join("");

  const body = Array.from(
    { length: rows },
    () =>
      `<tr>${Array.from(
        { length: columns },
        () => "<td>Enter value</td>",
      ).join("")}</tr>`,
  ).join("");

  return `<table><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table>`;
}

export function TableBlockEditor({
  block,
  disabled = false,
  onChange,
}: Props) {
  return (
    <div className="editor-v2-table-editor">
      <div className="editor-v2-table-actions">
        <span>Table size</span>

        <button
          type="button"
          disabled={disabled}
          onClick={() =>
            onChange({
              ...block,
              html: createTable(2, 2),
            })
          }
        >
          2 × 2
        </button>

        <button
          type="button"
          disabled={disabled}
          onClick={() =>
            onChange({
              ...block,
              html: createTable(3, 3),
            })
          }
        >
          3 × 3
        </button>

        <button
          type="button"
          disabled={disabled}
          onClick={() =>
            onChange({
              ...block,
              html: createTable(4, 4),
            })
          }
        >
          4 × 4
        </button>
      </div>

      <p className="editor-v2-support-note">
        Cell par click karke directly text edit karein.
      </p>

      <div
        className="editor-v2-editable-table"
        contentEditable={!disabled}
        suppressContentEditableWarning
        dangerouslySetInnerHTML={{ __html: block.html }}
        onBlur={event =>
          onChange({
            ...block,
            html: event.currentTarget.innerHTML,
          })
        }
      />
    </div>
  );
}
