"use client";

import { useEffect, useState } from "react";

import type { CmsGalleryBlock } from "@/lib/editor-v2/document-types";

type MediaAsset = {
  id: number;
  public_url: string;
  thumbnail_url?: string | null;
  original_filename: string;
  alt_text?: string;
};

type Props = {
  block: CmsGalleryBlock;
  disabled?: boolean;
  onChange: (block: CmsGalleryBlock) => void;
};

export function GalleryBlockEditor({
  block,
  disabled = false,
  onChange,
}: Props) {
  const [items, setItems] = useState<MediaAsset[]>([]);
  const [message, setMessage] = useState("Loading Media Library…");

  async function loadMedia() {
    setMessage("Loading Media Library…");

    try {
      const response = await fetch(
        "/api/admin/media?page=1&page_size=48&state=active",
        {
          cache: "no-store",
          credentials: "same-origin",
        },
      );

      const payload = (await response.json()) as {
        items?: MediaAsset[];
        detail?: string;
        message?: string;
      };

      if (!response.ok) {
        setMessage(
          payload.detail ||
            payload.message ||
            "Media Library could not be loaded.",
        );
        return;
      }

      setItems(payload.items || []);
      setMessage("");
    } catch {
      setMessage("Media service is temporarily unavailable.");
    }
  }

  useEffect(() => {
    void loadMedia();
  }, []);

  function toggleMedia(mediaId: number) {
    const selected = block.mediaIds.includes(mediaId);

    onChange({
      ...block,
      mediaIds: selected
        ? block.mediaIds.filter(id => id !== mediaId)
        : [...block.mediaIds, mediaId],
    });
  }

  const selectedItems = block.mediaIds
    .map(id => items.find(item => item.id === id))
    .filter((item): item is MediaAsset => Boolean(item));

  return (
    <div className="editor-v2-gallery-editor">
      <div className="editor-v2-gallery-settings">
        <label>
          <span>Columns</span>
          <select
            value={block.columns}
            disabled={disabled}
            onChange={event =>
              onChange({
                ...block,
                columns:
                  Number(event.target.value) as CmsGalleryBlock["columns"],
              })
            }
          >
            <option value={2}>2 columns</option>
            <option value={3}>3 columns</option>
            <option value={4}>4 columns</option>
            <option value={5}>5 columns</option>
          </select>
        </label>

        <label>
          <span>Gap in pixels</span>
          <input
            type="number"
            min={0}
            max={80}
            value={block.gap}
            disabled={disabled}
            onChange={event =>
              onChange({
                ...block,
                gap: Math.max(0, Number(event.target.value) || 0),
              })
            }
          />
        </label>

        <label className="editor-v2-check-field">
          <input
            type="checkbox"
            checked={block.lightbox}
            disabled={disabled}
            onChange={event =>
              onChange({ ...block, lightbox: event.target.checked })
            }
          />
          Enable lightbox
        </label>

        <label className="editor-v2-check-field">
          <input
            type="checkbox"
            checked={block.showCaptions}
            disabled={disabled}
            onChange={event =>
              onChange({
                ...block,
                showCaptions: event.target.checked,
              })
            }
          />
          Show captions
        </label>
      </div>

      <div className="editor-v2-gallery-summary">
        <strong>{block.mediaIds.length} images selected</strong>

        <button
          type="button"
          className="secondary-button"
          disabled={disabled}
          onClick={() => void loadMedia()}
        >
          Refresh library
        </button>

        <a href="/studio-v2/media" target="_blank">
          Upload new media ↗
        </a>
      </div>

      {selectedItems.length ? (
        <div
          className="editor-v2-gallery-preview"
          style={{
            gridTemplateColumns: `repeat(${block.columns}, minmax(0, 1fr))`,
            gap: `${block.gap}px`,
          }}
        >
          {selectedItems.map(item => (
            <figure key={item.id}>
              <img
                src={item.thumbnail_url || item.public_url}
                alt={item.alt_text || ""}
              />

              {block.showCaptions ? (
                <figcaption>{item.original_filename}</figcaption>
              ) : null}
            </figure>
          ))}
        </div>
      ) : null}

      <h3>Select images</h3>

      {message ? (
        <p className="editor-v2-support-note">{message}</p>
      ) : items.length ? (
        <div className="editor-v2-gallery-library">
          {items.map(item => {
            const selected = block.mediaIds.includes(item.id);

            return (
              <button
                type="button"
                key={item.id}
                disabled={disabled}
                className={selected ? "selected" : ""}
                onClick={() => toggleMedia(item.id)}
              >
                <img
                  src={item.thumbnail_url || item.public_url}
                  alt={item.alt_text || ""}
                />
                <span>{selected ? "Selected" : "Select"}</span>
              </button>
            );
          })}
        </div>
      ) : (
        <p>No active media found. Upload images first.</p>
      )}
    </div>
  );
}
