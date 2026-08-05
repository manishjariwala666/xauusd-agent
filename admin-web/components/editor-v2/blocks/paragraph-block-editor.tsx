"use client";

import type {
  CmsParagraphBlock,
} from "@/lib/editor-v2/document-types";

import {
  BlockRichTextEditor,
} from "../core/block-rich-text-editor";

type AutoEmbedInput = {
  url: string;
  beforeHtml: string;
  afterHtml: string;
};

type ParagraphBlockEditorProps = {
  block: CmsParagraphBlock;
  disabled?: boolean;
  onChange: (block: CmsParagraphBlock) => void;
  onAutoEmbed?: (input: AutoEmbedInput) => void;
};

function isYoutubeUrl(value: string): boolean {
  try {
    const url = new URL(value.trim());
    const hostname = url.hostname.toLowerCase();

    return (
      hostname === "youtu.be" ||
      hostname === "youtube.com" ||
      hostname.endsWith(".youtube.com")
    );
  } catch {
    return false;
  }
}

function findStandaloneYoutubeEmbed(
  html: string,
): AutoEmbedInput | null {
  if (typeof window === "undefined") return null;

  const container = document.createElement("div");
  container.innerHTML = html;

  const children = Array.from(container.children);

  for (const [index, child] of children.entries()) {
    const visibleText = String(child.textContent || "").trim();

    if (!visibleText || !isYoutubeUrl(visibleText)) {
      continue;
    }

    /*
     * Convert only a standalone URL paragraph. URLs mixed with
     * normal sentence text remain normal links.
     */
    const normalized = visibleText.replace(/\s+/g, "");

    if (normalized !== visibleText) {
      continue;
    }

    return {
      url: visibleText,
      beforeHtml: children
        .slice(0, index)
        .map(item => item.outerHTML)
        .join(""),
      afterHtml: children
        .slice(index + 1)
        .map(item => item.outerHTML)
        .join(""),
    };
  }

  return null;
}

export function ParagraphBlockEditor({
  block,
  disabled = false,
  onChange,
  onAutoEmbed,
}: ParagraphBlockEditorProps) {
  return (
    <div className="editor-v2-paragraph-editor">
      <BlockRichTextEditor
        value={block.html}
        disabled={disabled}
        placeholder="Write paragraph content…"
        onChange={html => {
          const autoEmbed = findStandaloneYoutubeEmbed(html);

          if (autoEmbed && onAutoEmbed) {
            onAutoEmbed(autoEmbed);
            return;
          }

          onChange({
            ...block,
            html,
          });
        }}
      />
    </div>
  );
}
