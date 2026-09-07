"use client";

import { useEffect, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import Underline from "@tiptap/extension-underline";
import { TextStyle } from "@tiptap/extension-text-style";
import Color from "@tiptap/extension-color";
import Highlight from "@tiptap/extension-highlight";
import Placeholder from "@tiptap/extension-placeholder";

type Props = {
  value: string;
  onChange: (value: string) => void;
};

const looksLikeHtml = (value: string) => /<\/?[a-z][\s\S]*>/i.test(value);

const escapeHtml = (value: string) =>
  value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");

const initialHtml = (value: string) => {
  if (!value.trim()) return "<p></p>";
  if (looksLikeHtml(value)) return value;

  return value
    .split(/\n{2,}/)
    .map(block => `<p>${escapeHtml(block).replaceAll("\n", "<br>")}</p>`)
    .join("");
};

export function RichContentEditor({ value, onChange }: Props) {
  const [linkPanel, setLinkPanel] = useState(false);
  const [linkUrl, setLinkUrl] = useState("");

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3, 4, 5] },
        link: false,
        underline: false,
      }),
      Underline,
      TextStyle,
      Color,
      Highlight.configure({ multicolor: true }),
      Link.configure({
        openOnClick: false,
        autolink: true,
        linkOnPaste: true,
        HTMLAttributes: {
          rel: "noopener noreferrer",
        },
      }),
      Placeholder.configure({
        placeholder: "Write your article here…",
      }),
    ],
    content: initialHtml(value),
    editorProps: {
      attributes: {
        class: "rich-editor-content",
        spellcheck: "true",
      },
    },
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
  });

  useEffect(() => {
    if (!editor || editor.isDestroyed) return;

    const current = editor.getHTML();
    const incoming = initialHtml(value);

    if (current !== incoming && !editor.isFocused) {
      editor.commands.setContent(incoming, { emitUpdate: false });
    }
  }, [editor, value]);

  if (!editor) {
    return <div className="rich-editor-loading">Loading editor…</div>;
  }

  const applyLink = () => {
    const url = linkUrl.trim();

    if (!url) return;

    editor
      .chain()
      .focus()
      .extendMarkRange("link")
      .setLink({ href: url })
      .run();

    setLinkPanel(false);
    setLinkUrl("");
  };

  const openLinkPanel = () => {
    const existing = editor.getAttributes("link").href as string | undefined;
    setLinkUrl(existing || "");
    setLinkPanel(true);
  };

  return (
    <div className="rich-editor-shell">
      <div className="rich-editor-toolbar" role="toolbar" aria-label="Article formatting">
        <select
          aria-label="Text style"
          value={
            editor.isActive("heading", { level: 1 }) ? "h1" :
            editor.isActive("heading", { level: 2 }) ? "h2" :
            editor.isActive("heading", { level: 3 }) ? "h3" :
            editor.isActive("heading", { level: 4 }) ? "h4" :
            editor.isActive("heading", { level: 5 }) ? "h5" : "p"
          }
          onChange={event => {
            const value = event.target.value;
            const chain = editor.chain().focus();

            if (value === "p") chain.setParagraph().run();
            else {
              chain.toggleHeading({
                level: Number(value.slice(1)) as 1 | 2 | 3 | 4 | 5,
              }).run();
            }
          }}
        >
          <option value="p">Paragraph</option>
          <option value="h1">Heading 1</option>
          <option value="h2">Heading 2</option>
          <option value="h3">Heading 3</option>
          <option value="h4">Heading 4</option>
          <option value="h5">Heading 5</option>
        </select>

        <button type="button" className={editor.isActive("bold") ? "active" : ""} onClick={() => editor.chain().focus().toggleBold().run()}><strong>B</strong></button>
        <button type="button" className={editor.isActive("italic") ? "active" : ""} onClick={() => editor.chain().focus().toggleItalic().run()}><em>I</em></button>
        <button type="button" className={editor.isActive("underline") ? "active" : ""} onClick={() => editor.chain().focus().toggleUnderline().run()}><u>U</u></button>
        <button type="button" className={editor.isActive("strike") ? "active" : ""} onClick={() => editor.chain().focus().toggleStrike().run()}><s>S</s></button>

        <button type="button" title="Bullet list" className={editor.isActive("bulletList") ? "active" : ""} onClick={() => editor.chain().focus().toggleBulletList().run()}>• List</button>
        <button type="button" title="Numbered list" className={editor.isActive("orderedList") ? "active" : ""} onClick={() => editor.chain().focus().toggleOrderedList().run()}>1. List</button>
        <button type="button" title="Quote" className={editor.isActive("blockquote") ? "active" : ""} onClick={() => editor.chain().focus().toggleBlockquote().run()}>❝</button>
        <button type="button" title="Divider" onClick={() => editor.chain().focus().setHorizontalRule().run()}>—</button>

        <button type="button" title="Insert or edit link" className={editor.isActive("link") ? "active" : ""} onClick={openLinkPanel}>🔗 Link</button>
        <button type="button" title="Remove link" disabled={!editor.isActive("link")} onClick={() => editor.chain().focus().unsetLink().run()}>Unlink</button>

        <label className="editor-colour-control" title="Text colour">
          A
          <input
            type="color"
            aria-label="Text colour"
            defaultValue="#111827"
            onChange={event => editor.chain().focus().setColor(event.target.value).run()}
          />
        </label>

        <label className="editor-colour-control highlight-control" title="Highlight colour">
          Highlight
          <input
            type="color"
            aria-label="Highlight colour"
            defaultValue="#fff59d"
            onChange={event => editor.chain().focus().toggleHighlight({ color: event.target.value }).run()}
          />
        </label>

        <button type="button" title="Clear colour and formatting" onClick={() => editor.chain().focus().unsetColor().unsetHighlight().clearNodes().unsetAllMarks().run()}>Clear</button>
        <button type="button" title="Undo" disabled={!editor.can().undo()} onClick={() => editor.chain().focus().undo().run()}>↶</button>
        <button type="button" title="Redo" disabled={!editor.can().redo()} onClick={() => editor.chain().focus().redo().run()}>↷</button>
      </div>

      {linkPanel && (
        <div className="rich-link-panel">
          <label>
            Internal or external URL
            <input
              autoFocus
              value={linkUrl}
              onChange={event => setLinkUrl(event.target.value)}
              placeholder="/blog/post-slug or https://example.com"
              onKeyDown={event => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  applyLink();
                }
                if (event.key === "Escape") setLinkPanel(false);
              }}
            />
          </label>

          <button type="button" className="primary-button" onClick={applyLink}>
            Apply link
          </button>

          <button type="button" className="secondary-button" onClick={() => setLinkPanel(false)}>
            Cancel
          </button>
        </div>
      )}

      <EditorContent editor={editor} />
    </div>
  );
}
