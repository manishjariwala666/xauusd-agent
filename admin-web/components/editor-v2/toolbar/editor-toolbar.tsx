"use client";

import type { Editor } from "@tiptap/react";

type EditorToolbarProps = {
  editor: Editor;
  disabled?: boolean;
  onOpenMedia: () => void;
};

export function EditorToolbar({
  editor,
  disabled = false,
  onOpenMedia,
}: EditorToolbarProps) {
  function setLink() {
    const currentHref = editor.getAttributes("link").href as string | undefined;
    const href = window.prompt("Enter link URL", currentHref || "https://");

    if (href === null) return;

    if (!href.trim()) {
      editor.chain().focus().extendMarkRange("link").unsetLink().run();
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
    <div
      className="editor-v2-toolbar"
      role="toolbar"
      aria-label="WordPress-style content toolbar"
    >
      <select
        aria-label="Text style"
        value={
          editor.isActive("heading", { level: 1 }) ? "h1"
            : editor.isActive("heading", { level: 2 }) ? "h2"
              : editor.isActive("heading", { level: 3 }) ? "h3"
                : editor.isActive("heading", { level: 4 }) ? "h4"
                  : editor.isActive("heading", { level: 5 }) ? "h5"
                    : editor.isActive("heading", { level: 6 }) ? "h6"
                      : "paragraph"
        }
        onChange={event => {
          const value = event.target.value;

          if (value === "paragraph") {
            editor.chain().focus().setParagraph().run();
            return;
          }

          const level = Number(value.replace("h", "")) as 1 | 2 | 3 | 4 | 5 | 6;
          editor.chain().focus().setHeading({ level }).run();
        }}
        disabled={disabled}
      >
        <option value="paragraph">Paragraph</option>
        <option value="h1">Heading 1</option>
        <option value="h2">Heading 2</option>
        <option value="h3">Heading 3</option>
        <option value="h4">Heading 4</option>
        <option value="h5">Heading 5</option>
        <option value="h6">Heading 6</option>
      </select>

      <span className="editor-v2-toolbar-divider" />

      <button
        type="button"
        className={editor.isActive("bold") ? "active" : ""}
        onClick={() => editor.chain().focus().toggleBold().run()}
        disabled={disabled}
        aria-label="Bold"
        title="Bold"
      >
        B
      </button>

      <button
        type="button"
        className={editor.isActive("italic") ? "active" : ""}
        onClick={() => editor.chain().focus().toggleItalic().run()}
        disabled={disabled}
        aria-label="Italic"
        title="Italic"
      >
        I
      </button>

      <button
        type="button"
        className={editor.isActive("underline") ? "active" : ""}
        onClick={() => editor.chain().focus().toggleUnderline().run()}
        disabled={disabled}
        aria-label="Underline"
        title="Underline"
      >
        U
      </button>

      <button
        type="button"
        className={editor.isActive("strike") ? "active" : ""}
        onClick={() => editor.chain().focus().toggleStrike().run()}
        disabled={disabled}
        aria-label="Strikethrough"
        title="Strikethrough"
      >
        S
      </button>

      <span className="editor-v2-toolbar-divider" />

      <button
        type="button"
        className={editor.isActive({ textAlign: "left" }) ? "active" : ""}
        onClick={() => editor.chain().focus().setTextAlign("left").run()}
        disabled={disabled}
        title="Align left"
      >
        Left
      </button>

      <button
        type="button"
        className={editor.isActive({ textAlign: "center" }) ? "active" : ""}
        onClick={() => editor.chain().focus().setTextAlign("center").run()}
        disabled={disabled}
        title="Align center"
      >
        Center
      </button>

      <button
        type="button"
        className={editor.isActive({ textAlign: "right" }) ? "active" : ""}
        onClick={() => editor.chain().focus().setTextAlign("right").run()}
        disabled={disabled}
        title="Align right"
      >
        Right
      </button>

      <button
        type="button"
        className={editor.isActive({ textAlign: "justify" }) ? "active" : ""}
        onClick={() => editor.chain().focus().setTextAlign("justify").run()}
        disabled={disabled}
        title="Justify"
      >
        Justify
      </button>

      <span className="editor-v2-toolbar-divider" />

      <button
        type="button"
        className={editor.isActive("bulletList") ? "active" : ""}
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        disabled={disabled}
      >
        Bullets
      </button>

      <button
        type="button"
        className={editor.isActive("orderedList") ? "active" : ""}
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        disabled={disabled}
      >
        Numbered
      </button>

      <button
        type="button"
        className={editor.isActive("blockquote") ? "active" : ""}
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
        disabled={disabled}
      >
        Quote
      </button>

      <button
        type="button"
        className={editor.isActive("codeBlock") ? "active" : ""}
        onClick={() => editor.chain().focus().toggleCodeBlock().run()}
        disabled={disabled}
      >
        Code
      </button>

      <button
        type="button"
        onClick={() => editor.chain().focus().setHorizontalRule().run()}
        disabled={disabled}
      >
        Line
      </button>

      <span className="editor-v2-toolbar-divider" />

      <button type="button" onClick={setLink} disabled={disabled}>
        Link
      </button>

      <button
        type="button"
        onClick={() =>
          editor.chain().focus().extendMarkRange("link").unsetLink().run()
        }
        disabled={disabled || !editor.isActive("link")}
      >
        Unlink
      </button>

      <button type="button" onClick={onOpenMedia} disabled={disabled}>
        Add Media
      </button>

      <button
        type="button"
        onClick={() =>
          editor
            .chain()
            .focus()
            .insertTable({
              rows: 3,
              cols: 3,
              withHeaderRow: true,
            })
            .run()
        }
        disabled={disabled}
      >
        Table
      </button>

      <span className="editor-v2-toolbar-divider" />

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
  );
}
