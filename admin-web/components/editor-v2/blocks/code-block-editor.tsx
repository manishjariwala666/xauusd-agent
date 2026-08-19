"use client";

import type { CmsCodeBlock } from "@/lib/editor-v2/document-types";

type Props = {
  block: CmsCodeBlock;
  disabled?: boolean;
  onChange: (block: CmsCodeBlock) => void;
};

export function CodeBlockEditor({
  block,
  disabled = false,
  onChange,
}: Props) {
  return (
    <div className="editor-v2-code-editor">
      <label>
        <span>Language</span>

        <select
          value={block.language}
          disabled={disabled}
          onChange={event =>
            onChange({
              ...block,
              language: event.target.value,
            })
          }
        >
          <option value="text">Plain text</option>
          <option value="javascript">JavaScript</option>
          <option value="typescript">TypeScript</option>
          <option value="python">Python</option>
          <option value="html">HTML</option>
          <option value="css">CSS</option>
          <option value="json">JSON</option>
          <option value="bash">Bash</option>
          <option value="sql">SQL</option>
        </select>
      </label>

      <label>
        <span>Code</span>

        <textarea
          value={block.code}
          disabled={disabled}
          rows={12}
          spellCheck={false}
          placeholder="Paste or write code here…"
          onChange={event =>
            onChange({
              ...block,
              code: event.target.value,
            })
          }
        />
      </label>
    </div>
  );
}
