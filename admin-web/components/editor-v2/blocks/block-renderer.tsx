"use client";

import type { CmsBlock } from "@/lib/editor-v2/document-types";

import { AccordionBlockEditor } from "./accordion-block-editor";
import { ButtonBlockEditor } from "./button-block-editor";
import { CodeBlockEditor } from "./code-block-editor";
import { DividerBlockEditor } from "./divider-block-editor";
import { GalleryBlockEditor } from "./gallery-block-editor";
import { HeadingBlockEditor } from "./heading-block-editor";
import { ImageBlockEditor } from "./image-block-editor";
import { ListBlockEditor } from "./list-block-editor";
import { ParagraphBlockEditor } from "./paragraph-block-editor";
import { QuoteBlockEditor } from "./quote-block-editor";
import { TableBlockEditor } from "./table-block-editor";
import { YouTubeBlockEditor } from "./youtube-block-editor";

type Props = {
  block: CmsBlock;
  index: number;
  total: number;
  disabled?: boolean;
  onChange: (block: CmsBlock) => void;
  onAutoEmbed?: (input: {
    url: string;
    beforeHtml: string;
    afterHtml: string;
  }) => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onDuplicate: () => void;
  onRemove: () => void;
};

export function BlockRenderer({
  block,
  index,
  total,
  disabled = false,
  onChange,
  onAutoEmbed,
  onMoveUp,
  onMoveDown,
  onDuplicate,
  onRemove,
}: Props) {
  let editorContent;

  switch (block.type) {
    case "paragraph":
      editorContent = (
        <ParagraphBlockEditor
          block={block}
          disabled={disabled}
          onChange={onChange}
          onAutoEmbed={onAutoEmbed}
        />
      );
      break;
    case "heading":
      editorContent = (
        <HeadingBlockEditor
          block={block}
          disabled={disabled}
          onChange={onChange}
        />
      );
      break;
    case "image":
      editorContent = (
        <ImageBlockEditor
          block={block}
          disabled={disabled}
          onChange={onChange}
        />
      );
      break;
    case "gallery":
      editorContent = (
        <GalleryBlockEditor
          block={block}
          disabled={disabled}
          onChange={onChange}
        />
      );
      break;
    case "table":
      editorContent = (
        <TableBlockEditor
          block={block}
          disabled={disabled}
          onChange={onChange}
        />
      );
      break;
    case "bullet-list":
    case "numbered-list":
      editorContent = (
        <ListBlockEditor
          block={block}
          disabled={disabled}
          onChange={onChange}
        />
      );
      break;
    case "quote":
      editorContent = (
        <QuoteBlockEditor
          block={block}
          disabled={disabled}
          onChange={onChange}
        />
      );
      break;
    case "code":
      editorContent = (
        <CodeBlockEditor
          block={block}
          disabled={disabled}
          onChange={onChange}
        />
      );
      break;
    case "button":
      editorContent = (
        <ButtonBlockEditor
          block={block}
          disabled={disabled}
          onChange={onChange}
        />
      );
      break;
    case "divider":
      editorContent = (
        <DividerBlockEditor
          block={block}
          disabled={disabled}
          onChange={onChange}
        />
      );
      break;
    case "accordion":
      editorContent = (
        <AccordionBlockEditor
          block={block}
          disabled={disabled}
          onChange={onChange}
        />
      );
      break;
    case "youtube":
      editorContent = (
        <YouTubeBlockEditor
          block={block}
          disabled={disabled}
          onChange={onChange}
        />
      );
      break;
  }

  return (
    <section
      className="wp-content-block"
      data-block-id={block.id}
      data-block-type={block.type}
    >
      <div
        className="wp-block-toolbar"
        role="toolbar"
        aria-label={`${block.type} block controls`}
      >
        <span className="wp-block-type">{block.type}</span>

        <button
          type="button"
          disabled={disabled || index === 0}
          onClick={onMoveUp}
          title="Move up"
        >
          ↑
        </button>

        <button
          type="button"
          disabled={disabled || index === total - 1}
          onClick={onMoveDown}
          title="Move down"
        >
          ↓
        </button>

        <button
          type="button"
          disabled={disabled}
          onClick={onDuplicate}
          title="Duplicate"
        >
          Duplicate
        </button>

        <button
          type="button"
          disabled={disabled}
          onClick={onRemove}
          className="danger-link"
          title="Remove"
        >
          Remove
        </button>
      </div>

      <div className="wp-block-content">
        {editorContent}
      </div>
    </section>
  );
}
