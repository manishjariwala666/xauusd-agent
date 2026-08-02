"use client";

import { useEffect, useMemo } from "react";
import { EditorContent, useEditor } from "@tiptap/react";

import { createEditorV2Extensions } from "@/lib/editor-v2/extensions";

type BlockRichTextEditorProps = {
  value: string;
  disabled?: boolean;
  placeholder?: string;
  onChange: (html: string) => void;
};

export function BlockRichTextEditor({
  value,
  disabled = false,
  placeholder = "Start writing…",
  onChange,
}: BlockRichTextEditorProps) {
  const extensions = useMemo(
    () => createEditorV2Extensions(placeholder),
    [placeholder],
  );

  const editor = useEditor({
    immediatelyRender: false,
    editable: !disabled,
    extensions,
    content: value || "<p></p>",
    onUpdate: ({ editor: currentEditor }) => {
      onChange(currentEditor.getHTML());
    },
    editorProps: {
      attributes: {
        class: "editor-v2-rich-block-content",
        spellcheck: "true",
        role: "textbox",
        "aria-multiline": "true",
        "aria-label": "Rich text paragraph",
      },
    },
  });

  useEffect(() => {
    if (!editor) return;

    const nextHtml = value || "<p></p>";

    if (editor.getHTML() !== nextHtml) {
      editor.commands.setContent(nextHtml, {
        emitUpdate: false,
      });
    }
  }, [editor, value]);

  useEffect(() => {
    if (!editor) return;
    editor.setEditable(!disabled);
  }, [disabled, editor]);

  if (!editor) {
    return (
      <div className="editor-v2-rich-block-loading">
        Loading visual editor…
      </div>
    );
  }

  function setLink() {
    if (!editor) return;

    const currentHref =
      editor.getAttributes("link").href as string | undefined;

    const href = window.prompt(
      "Enter link URL",
      currentHref || "https://",
    );

    if (href === null) return;

    if (!href.trim()) {
      editor
        .chain()
        .focus()
        .extendMarkRange("link")
        .unsetLink()
        .run();

      return;
    }

    if (editor.state.selection.empty) {
      const label = window.prompt(
        "Link text",
        "Open link",
      );

      if (!label?.trim()) return;

      editor
        .chain()
        .focus()
        .insertContent({
          type: "text",
          text: label.trim(),
          marks: [
            {
              type: "link",
              attrs: {
                href: href.trim(),
                target: "_blank",
                rel: "noopener noreferrer",
              },
            },
          ],
        })
        .run();

      return;
    }

    editor
      .chain()
      .focus()
      .extendMarkRange("link")
      .setLink({
        href: href.trim(),
        target: "_blank",
        rel: "noopener noreferrer",
      })
      .run();
  }

  return (
    <section className="editor-v2-rich-block">
      <div
        className="editor-v2-rich-block-toolbar"
        role="toolbar"
        aria-label="Text formatting"
      >
        <button
          type="button"
          className={editor.isActive("bold") ? "active" : ""}
          onClick={() => editor.chain().focus().toggleBold().run()}
          disabled={disabled}
          title="Bold"
        >
          B
        </button>

        <button
          type="button"
          className={editor.isActive("italic") ? "active" : ""}
          onClick={() => editor.chain().focus().toggleItalic().run()}
          disabled={disabled}
          title="Italic"
        >
          I
        </button>

        <button
          type="button"
          className={editor.isActive("underline") ? "active" : ""}
          onClick={() =>
            editor.chain().focus().toggleUnderline().run()
          }
          disabled={disabled}
          title="Underline"
        >
          U
        </button>

        <button
          type="button"
          className={editor.isActive("strike") ? "active" : ""}
          onClick={() => editor.chain().focus().toggleStrike().run()}
          disabled={disabled}
          title="Strikethrough"
        >
          S
        </button>

        <span className="editor-v2-toolbar-divider" />

        <button
          type="button"
          className={
            editor.isActive("bulletList") ? "active" : ""
          }
          onClick={() =>
            editor.chain().focus().toggleBulletList().run()
          }
          disabled={disabled}
        >
          Bullets
        </button>

        <button
          type="button"
          className={
            editor.isActive("orderedList") ? "active" : ""
          }
          onClick={() =>
            editor.chain().focus().toggleOrderedList().run()
          }
          disabled={disabled}
        >
          Numbered
        </button>

        <button
          type="button"
          className={
            editor.isActive("blockquote") ? "active" : ""
          }
          onClick={() =>
            editor.chain().focus().toggleBlockquote().run()
          }
          disabled={disabled}
        >
          Quote
        </button>

        <span className="editor-v2-toolbar-divider" />

        <button
          type="button"
          className={
            editor.isActive({ textAlign: "left" }) ? "active" : ""
          }
          onClick={() =>
            editor.chain().focus().setTextAlign("left").run()
          }
          disabled={disabled}
        >
          Left
        </button>

        <button
          type="button"
          className={
            editor.isActive({ textAlign: "center" })
              ? "active"
              : ""
          }
          onClick={() =>
            editor.chain().focus().setTextAlign("center").run()
          }
          disabled={disabled}
        >
          Center
        </button>

        <button
          type="button"
          className={
            editor.isActive({ textAlign: "right" }) ? "active" : ""
          }
          onClick={() =>
            editor.chain().focus().setTextAlign("right").run()
          }
          disabled={disabled}
        >
          Right
        </button>

        <button
          type="button"
          className={
            editor.isActive({ textAlign: "justify" })
              ? "active"
              : ""
          }
          onClick={() =>
            editor.chain().focus().setTextAlign("justify").run()
          }
          disabled={disabled}
        >
          Justify
        </button>

        <span className="editor-v2-toolbar-divider" />

        <button
          type="button"
          onClick={setLink}
          disabled={disabled}
        >
          Link
        </button>

        <button
          type="button"
          onClick={() =>
            editor
              .chain()
              .focus()
              .extendMarkRange("link")
              .unsetLink()
              .run()
          }
          disabled={disabled || !editor.isActive("link")}
        >
          Unlink
        </button>

        <button
          type="button"
          onClick={() =>
            editor.chain().focus().setHorizontalRule().run()
          }
          disabled={disabled}
        >
          Line
        </button>

        <button
          type="button"
          onClick={() => editor.chain().focus().undo().run()}
          disabled={disabled || !editor.can().undo()}
        >
          Undo
        </button>

        <button
          type="button"
          onClick={() => editor.chain().focus().redo().run()}
          disabled={disabled || !editor.can().redo()}
        >
          Redo
        </button>
      </div>

      <EditorContent editor={editor} />
    </section>
  );
}
