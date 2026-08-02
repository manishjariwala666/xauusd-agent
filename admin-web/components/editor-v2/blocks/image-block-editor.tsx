"use client";

import { useState } from "react";

import {
  MediaLibraryDialog,
  type MediaLibraryAsset,
} from "../../media-library-dialog";

import type {
  CmsImageBlock,
} from "@/lib/editor-v2/document-types";

type ImageBlockEditorProps = {
  block: CmsImageBlock;
  disabled?: boolean;
  onChange: (block: CmsImageBlock) => void;
};

export function ImageBlockEditor({
  block,
  disabled = false,
  onChange,
}: ImageBlockEditorProps) {
  const [mediaOpen, setMediaOpen] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);

  function selectMedia(asset: MediaLibraryAsset) {
    setImageFailed(false);

    onChange({
      ...block,
      mediaId: asset.id,
      src: asset.public_url,
      alt: asset.alt_text || "",
      caption: asset.caption || "",
      width: null,
      height: null,
    });
  }

  function removeImage() {
    setImageFailed(false);

    onChange({
      ...block,
      mediaId: null,
      src: "",
      alt: "",
      caption: "",
      width: null,
      height: null,
      linkUrl: "",
    });
  }

  return (
    <div className="editor-v2-image-editor">
      {block.src && !imageFailed ? (
        <figure
          className={`editor-v2-image-preview align-${block.alignment}`}
        >
          <img
            src={block.src}
            alt={block.alt}
            onError={() => setImageFailed(true)}
            style={{
              width: block.width ? `${block.width}px` : undefined,
              height: block.height ? `${block.height}px` : undefined,
            }}
          />

          {block.caption ? (
            <figcaption>{block.caption}</figcaption>
          ) : null}
        </figure>
      ) : (
        <div className="editor-v2-image-empty">
          <strong>
            {imageFailed
              ? "Image file could not be loaded"
              : "No image selected"}
          </strong>

          <span>
            Choose an existing image or upload a new one.
          </span>
        </div>
      )}

      <div className="editor-v2-image-actions">
        <button
          type="button"
          className="primary-button"
          disabled={disabled}
          onClick={() => setMediaOpen(true)}
        >
          {block.src ? "Replace image" : "Choose from Media Library"}
        </button>

        {block.src ? (
          <button
            type="button"
            className="text-button danger-link"
            disabled={disabled}
            onClick={removeImage}
          >
            Remove image
          </button>
        ) : null}
      </div>

      <div className="editor-v2-image-fields">
        <label>
          <span>Image URL</span>
          <input
            value={block.src}
            disabled={disabled}
            onChange={event => {
              setImageFailed(false);

              onChange({
                ...block,
                mediaId: null,
                src: event.target.value,
              });
            }}
            placeholder="Select from Media Library or enter URL"
          />
        </label>

        <label>
          <span>Alt text</span>
          <input
            value={block.alt}
            disabled={disabled}
            onChange={event =>
              onChange({
                ...block,
                alt: event.target.value,
              })
            }
            maxLength={500}
            placeholder="Describe the image for accessibility and SEO"
          />
        </label>

        <label>
          <span>Caption</span>
          <textarea
            value={block.caption}
            disabled={disabled}
            onChange={event =>
              onChange({
                ...block,
                caption: event.target.value,
              })
            }
            rows={2}
            maxLength={2000}
            placeholder="Optional caption shown below the image"
          />
        </label>

        <label>
          <span>Alignment</span>
          <select
            value={block.alignment}
            disabled={disabled}
            onChange={event =>
              onChange({
                ...block,
                alignment:
                  event.target.value as CmsImageBlock["alignment"],
              })
            }
          >
            <option value="left">Left</option>
            <option value="center">Center</option>
            <option value="right">Right</option>
            <option value="wide">Wide</option>
            <option value="full">Full width</option>
          </select>
        </label>

        <label>
          <span>Width in pixels</span>
          <input
            type="number"
            min={1}
            max={4000}
            value={block.width ?? ""}
            disabled={disabled}
            onChange={event =>
              onChange({
                ...block,
                width: event.target.value
                  ? Number(event.target.value)
                  : null,
              })
            }
            placeholder="Automatic"
          />
        </label>

        <label>
          <span>Height in pixels</span>
          <input
            type="number"
            min={1}
            max={4000}
            value={block.height ?? ""}
            disabled={disabled}
            onChange={event =>
              onChange({
                ...block,
                height: event.target.value
                  ? Number(event.target.value)
                  : null,
              })
            }
            placeholder="Automatic"
          />
        </label>

        <label>
          <span>Link URL</span>
          <input
            value={block.linkUrl}
            disabled={disabled}
            onChange={event =>
              onChange({
                ...block,
                linkUrl: event.target.value,
              })
            }
            placeholder="Optional destination URL"
          />
        </label>
      </div>

      <MediaLibraryDialog
        open={mediaOpen}
        onClose={() => setMediaOpen(false)}
        onSelect={selectMedia}
      />
    </div>
  );
}
