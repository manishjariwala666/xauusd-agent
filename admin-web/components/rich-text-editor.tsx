"use client";

import { useEffect, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import Image from "@tiptap/extension-image";
import Placeholder from "@tiptap/extension-placeholder";
import TextAlign from "@tiptap/extension-text-align";
import { Table } from "@tiptap/extension-table";
import TableRow from "@tiptap/extension-table-row";
import TableHeader from "@tiptap/extension-table-header";
import TableCell from "@tiptap/extension-table-cell";
import {
  MediaLibraryDialog,
  type MediaLibraryAsset,
} from "./media-library-dialog";

type RichTextEditorProps = {
  value: string;
  onChange: (html: string) => void;
  disabled?: boolean;
  placeholder?: string;
};

export function RichTextEditor({
  value,
  onChange,
  disabled = false,
  placeholder = "Start writing…",
}: RichTextEditorProps) {
  const [mediaLibraryOpen, setMediaLibraryOpen] = useState(false);

  const editor = useEditor({
    immediatelyRender: false,
    editable: !disabled,
    extensions: [
      StarterKit,
      Link.configure({
        openOnClick: false,
        autolink: true,
        defaultProtocol: "https",
      }),
      Image.configure({
        allowBase64: false,
        inline: false,
      }),
      Placeholder.configure({
        placeholder,
      }),
      TextAlign.configure({
        types: ["heading", "paragraph"],
      }),
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableHeader,
      TableCell,
    ],
    content: value || "",
    onUpdate: ({ editor: currentEditor }) => {
      onChange(currentEditor.getHTML());
    },
    editorProps: {
      attributes: {
        class: "rich-editor-content",
        spellcheck: "true",
      },
    },
  });

  useEffect(() => {
    if (!editor) return;

    const currentHtml = editor.getHTML();
    const nextHtml = value || "";

    if (currentHtml !== nextHtml) {
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
      <div className="rich-editor-shell rich-editor-loading">
        Loading editor…
      </div>
    );
  }

  function setLink() {
    if (!editor) return;

    const previousUrl = editor.getAttributes("link").href as string | undefined;
    const url = window.prompt("Enter link URL", previousUrl || "https://");

    if (url === null) return;

    if (!url.trim()) {
      editor.chain().focus().extendMarkRange("link").unsetLink().run();
      return;
    }

    editor
      .chain()
      .focus()
      .extendMarkRange("link")
      .setLink({ href: url.trim() })
      .run();
  }

  function addImageByUrl() {
    if (!editor) return;

    const url = window.prompt("Enter image URL");

    if (!url?.trim()) return;

    editor
      .chain()
      .focus()
      .setImage({
        src: url.trim(),
        alt: "",
        title: "",
      })
      .run();
  }

  function insertMediaAsset(asset: MediaLibraryAsset) {
    if (!editor) return;

    editor
      .chain()
      .focus()
      .setImage({
        src: asset.public_url,
        alt: asset.alt_text || "",
        title: asset.caption || asset.original_filename,
      })
      .run();
  }

  return (
    <section className="rich-editor-shell">
      <div className="rich-editor-toolbar" role="toolbar" aria-label="Article formatting">
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBold().run()}
          className={editor.isActive("bold") ? "active" : ""}
          aria-pressed={editor.isActive("bold")}
        >
          Bold
        </button>

        <button
          type="button"
          onClick={() => editor.chain().focus().toggleItalic().run()}
          className={editor.isActive("italic") ? "active" : ""}
          aria-pressed={editor.isActive("italic")}
        >
          Italic
        </button>

        <button
          type="button"
          onClick={() => editor.chain().focus().toggleUnderline().run()}
          className={editor.isActive("underline") ? "active" : ""}
          aria-pressed={editor.isActive("underline")}
        >
          Underline
        </button>

        <button
          type="button"
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          className={editor.isActive("heading", { level: 2 }) ? "active" : ""}
          aria-pressed={editor.isActive("heading", { level: 2 })}
        >
          H2
        </button>

        <button
          type="button"
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
          className={editor.isActive("heading", { level: 3 }) ? "active" : ""}
          aria-pressed={editor.isActive("heading", { level: 3 })}
        >
          H3
        </button>

        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          className={editor.isActive("bulletList") ? "active" : ""}
          aria-pressed={editor.isActive("bulletList")}
        >
          Bullets
        </button>

        <button
          type="button"
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className={editor.isActive("orderedList") ? "active" : ""}
          aria-pressed={editor.isActive("orderedList")}
        >
          Numbered
        </button>

        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
          className={editor.isActive("blockquote") ? "active" : ""}
          aria-pressed={editor.isActive("blockquote")}
        >
          Quote
        </button>

        <button type="button" onClick={setLink}>
          Link
        </button>

        <button
          type="button"
          onClick={() => setMediaLibraryOpen(true)}
        >
          Media Library
        </button>

        <button type="button" onClick={addImageByUrl}>
          Image URL
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
        >
          Table
        </button>

        <button
          type="button"
          onClick={() => editor.chain().focus().undo().run()}
          disabled={!editor.can().undo()}
        >
          Undo
        </button>

        <button
          type="button"
          onClick={() => editor.chain().focus().redo().run()}
          disabled={!editor.can().redo()}
        >
          Redo
        </button>
      </div>

      <EditorContent editor={editor} />

      <MediaLibraryDialog
        open={mediaLibraryOpen}
        onClose={() => setMediaLibraryOpen(false)}
        onSelect={insertMediaAsset}
      />
    </section>
  );
}
