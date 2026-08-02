"use client";

import { useEffect, useMemo, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";

import { createEditorV2Extensions } from "@/lib/editor-v2/extensions";
import type { EditorV2Props } from "@/lib/editor-v2/types";
import { EditorToolbar } from "../toolbar/editor-toolbar";
import {
  MediaLibraryDialog,
  type MediaLibraryAsset,
} from "../../media-library-dialog";

export function EditorV2({
  value,
  onChange,
  disabled = false,
  placeholder = "Start writing your article…",
  className = "",
}: EditorV2Props) {
  const [mediaOpen, setMediaOpen] = useState(false);

  const extensions = useMemo(
    () => createEditorV2Extensions(placeholder),
    [placeholder],
  );

  const editor = useEditor({
    immediatelyRender: false,
    editable: !disabled,
    extensions,
    content: value || "",
    onUpdate: ({ editor: currentEditor }) => {
      onChange(currentEditor.getHTML());
    },
    editorProps: {
      attributes: {
        class: "editor-v2-content",
        spellcheck: "true",
        role: "textbox",
        "aria-multiline": "true",
        "aria-label": "Article content editor",
      },
    },
  });

  useEffect(() => {
    if (!editor) return;

    const nextValue = value || "";

    if (editor.getHTML() !== nextValue) {
      editor.commands.setContent(nextValue, {
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
      <div className="editor-v2-shell editor-v2-loading">
        Loading WordPress-style editor…
      </div>
    );
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
    <section className={`editor-v2-shell ${className}`.trim()}>
      <EditorToolbar
        editor={editor}
        disabled={disabled}
        onOpenMedia={() => setMediaOpen(true)}
      />

      <div className="editor-v2-workspace">
        <EditorContent editor={editor} />
      </div>

      <MediaLibraryDialog
        open={mediaOpen}
        onClose={() => setMediaOpen(false)}
        onSelect={insertMediaAsset}
      />
    </section>
  );
}
