"use client";

import { useEffect, useMemo, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";

import { createEditorV2Extensions } from "@/lib/editor-v2/extensions";
import {
  LinkSettingsModal,
  type LinkSettingsValue,
} from "../dialogs/link-settings-modal";

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
  const [linkModalOpen, setLinkModalOpen] =
    useState(false);
  const [linkSelectionEmpty, setLinkSelectionEmpty] =
    useState(false);
  const [linkInitialValue, setLinkInitialValue] =
    useState<LinkSettingsValue>({
      href: "",
      text: "",
      openInNewTab: false,
      nofollow: false,
      sponsored: false,
      ugc: false,
      underline: true,
      title: "",
      ariaLabel: "",
    });

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

  function openLinkSettings() {
    if (!editor) return;

    const attributes = editor.getAttributes("link") as {
      href?: string;
      target?: string | null;
      rel?: string | null;
      underline?: boolean;
      title?: string | null;
      ariaLabel?: string | null;
    };

    const { from, to, empty } = editor.state.selection;
    const selectedText = empty
      ? ""
      : editor.state.doc.textBetween(from, to, " ");

    const relTokens = String(attributes.rel || "")
      .toLowerCase()
      .split(/\s+/)
      .filter(Boolean);

    setLinkSelectionEmpty(empty);
    setLinkInitialValue({
      href: String(attributes.href || ""),
      text: selectedText,
      openInNewTab: attributes.target === "_blank",
      nofollow: relTokens.includes("nofollow"),
      sponsored: relTokens.includes("sponsored"),
      ugc: relTokens.includes("ugc"),
      underline: attributes.underline !== false,
      title: String(attributes.title || ""),
      ariaLabel: String(attributes.ariaLabel || ""),
    });
    setLinkModalOpen(true);
  }

  function saveLink(settings: LinkSettingsValue) {
    if (!editor) return;

    const rel = [
      settings.openInNewTab ? "noopener" : "",
      settings.openInNewTab ? "noreferrer" : "",
      settings.nofollow ? "nofollow" : "",
      settings.sponsored ? "sponsored" : "",
      settings.ugc ? "ugc" : "",
    ]
      .filter(Boolean)
      .join(" ");

    const attributes = {
      href: settings.href.trim(),
      target: settings.openInNewTab ? "_blank" : null,
      rel: rel || null,
      underline: settings.underline,
      title: settings.title.trim() || null,
      ariaLabel: settings.ariaLabel.trim() || null,
    };

    if (linkSelectionEmpty) {
      editor
        .chain()
        .focus()
        .insertContent({
          type: "text",
          text: settings.text.trim(),
          marks: [
            {
              type: "link",
              attrs: attributes,
            },
          ],
        })
        .run();
    } else {
      editor
        .chain()
        .focus()
        .extendMarkRange("link")
        .setLink(attributes)
        .run();
    }

    setLinkModalOpen(false);
  }

  function removeLink() {
    if (!editor) return;

    editor
      .chain()
      .focus()
      .extendMarkRange("link")
      .unsetLink()
      .run();

    setLinkModalOpen(false);
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

        <button
          type="button"
          className={
            editor.isActive("heading", { level: 2 })
              ? "active"
              : ""
          }
          onClick={() =>
            editor
              .chain()
              .focus()
              .toggleHeading({ level: 2 })
              .run()
          }
          disabled={disabled}
        >
          H2
        </button>

        <button
          type="button"
          className={
            editor.isActive("heading", { level: 3 })
              ? "active"
              : ""
          }
          onClick={() =>
            editor
              .chain()
              .focus()
              .toggleHeading({ level: 3 })
              .run()
          }
          disabled={disabled}
        >
          H3
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
          onClick={openLinkSettings}
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

      <LinkSettingsModal
        open={linkModalOpen}
        initialValue={linkInitialValue}
        allowTextEditing={linkSelectionEmpty}
        onClose={() => setLinkModalOpen(false)}
        onSave={saveLink}
        onRemove={removeLink}
      />
    </section>
  );
}
