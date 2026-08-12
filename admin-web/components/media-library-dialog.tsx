"use client";

import { useEffect, useRef, useState } from "react";
import { readMediaResponse } from "@/lib/media-response";
import { prepareMediaUpload } from "@/lib/media-upload";

export type MediaLibraryAsset = {
  id: number;
  public_url: string;
  thumbnail_url?: string | null;
  original_filename: string;
  alt_text?: string;
  caption?: string;
  width?: number;
  height?: number;
};

type MediaLibraryDialogProps = {
  open: boolean;
  onClose: () => void;
  onSelect: (asset: MediaLibraryAsset) => void;
};

function normalizeMediaLibraryAsset(value: unknown): MediaLibraryAsset | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;

  const payload = value as Record<string, unknown>;
  const candidate =
    payload.item && typeof payload.item === "object" && !Array.isArray(payload.item)
      ? payload.item as Record<string, unknown>
      : payload;
  const id = Number(candidate.id);

  if (!Number.isInteger(id) || id <= 0) return null;

  return {
    id,
    public_url: typeof candidate.public_url === "string" ? candidate.public_url : "",
    thumbnail_url:
      typeof candidate.thumbnail_url === "string"
        ? candidate.thumbnail_url
        : null,
    original_filename:
      typeof candidate.original_filename === "string" && candidate.original_filename.trim()
        ? candidate.original_filename
        : `media-${id}`,
    alt_text: typeof candidate.alt_text === "string" ? candidate.alt_text : "",
    caption: typeof candidate.caption === "string" ? candidate.caption : "",
    width: Number.isFinite(Number(candidate.width)) ? Number(candidate.width) : undefined,
    height: Number.isFinite(Number(candidate.height)) ? Number(candidate.height) : undefined,
  };
}

async function csrfToken(): Promise<string> {
  const response = await fetch("/api/admin/auth/csrf", {
    cache: "no-store",
    credentials: "same-origin",
  });

  if (!response.ok) {
    throw new Error("CSRF initialization failed.");
  }

  const payload = (await response.json()) as { csrfToken?: string };

  if (!payload.csrfToken) {
    throw new Error("CSRF token is missing.");
  }

  return payload.csrfToken;
}

export function MediaLibraryDialog({
  open,
  onClose,
  onSelect,
}: MediaLibraryDialogProps) {
  const [items, setItems] = useState<MediaLibraryAsset[]>([]);
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadPreviewUrl, setUploadPreviewUrl] = useState("");
  const [uploadAlt, setUploadAlt] = useState("");
  const [uploadCaption, setUploadCaption] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  function chooseAsset(value: unknown) {
    const asset = normalizeMediaLibraryAsset(value);

    if (!asset) {
      setMessage("Selected media item is invalid. Refresh the Media Library and try again.");
      return false;
    }

    onSelect(asset);
    onClose();
    return true;
  }

  function acceptUploadFile(file: File | null) {
    if (!file) return;

    const allowedTypes = new Set([
      "image/jpeg",
      "image/png",
      "image/webp",
      "image/gif",
    ]);

    if (!allowedTypes.has(file.type)) {
      setUploadFile(null);
      setMessage("Only JPEG, PNG, WebP or GIF images are allowed.");
      return;
    }

    if (file.size > 8 * 1024 * 1024) {
      setUploadFile(null);
      setMessage("Image must be 8 MB or smaller.");
      return;
    }

    setUploadFile(file);
    setMessage("");
  }

  async function loadMedia(term = "") {
    setBusy(true);
    setMessage("");

    try {
      const response = await fetch(
        `/api/admin/media?page_size=24&state=active&search=${encodeURIComponent(term)}`,
        {
          cache: "no-store",
          credentials: "same-origin",
        },
      );

      const payload = (await response.json()) as {
        items?: unknown[];
        message?: string;
        detail?: string;
      };

      if (!response.ok) {
        setMessage(
          payload.detail ||
            payload.message ||
            "Media Library could not be loaded.",
        );
        return;
      }

      setItems(
        (payload.items || [])
          .map(normalizeMediaLibraryAsset)
          .filter((item): item is MediaLibraryAsset => item !== null),
      );
    } catch {
      setMessage("Media service is temporarily unavailable.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!open) return;
    void loadMedia();
  }, [open]);

  useEffect(() => {
    if (!uploadFile) {
      setUploadPreviewUrl("");
      return;
    }

    const objectUrl = URL.createObjectURL(uploadFile);
    setUploadPreviewUrl(objectUrl);

    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [uploadFile]);

  async function upload() {
    if (!uploadFile) {
      setMessage("Choose an image before uploading.");
      return;
    }

    setBusy(true);
    setMessage("");

    try {
      const preparedFile = await prepareMediaUpload(uploadFile);
      const token = await csrfToken();
      const formData = new FormData();

      formData.set("file", preparedFile);
      formData.set("alt_text", uploadAlt.trim());
      formData.set("caption", uploadCaption.trim());

      const response = await fetch("/api/admin/media/upload", {
        method: "POST",
        headers: {
          "X-CSRF-Token": token,
        },
        body: formData,
        credentials: "same-origin",
      });

      const payload = await readMediaResponse<unknown>(response);

      if (!response.ok) {
        const errorPayload =
          payload && typeof payload === "object"
            ? payload as { detail?: string; message?: string }
            : {};
        setMessage(
          errorPayload.detail ||
            errorPayload.message ||
            "Image upload could not be completed.",
        );
        return;
      }

      if (!chooseAsset(payload)) return;
      setUploadFile(null);
      setUploadPreviewUrl("");
      setUploadAlt("");
      setUploadCaption("");
      setUploading(false);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Media upload is temporarily unavailable.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!open) return null;

  return (
    <div
      className="media-library-backdrop"
      role="presentation"
      onMouseDown={event => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="media-library-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="media-library-title"
      >
        <header className="media-library-header">
          <div>
            <span className="section-kicker">MEDIA LIBRARY</span>
            <h2 id="media-library-title">Choose an image</h2>
            <p>Select an existing asset or upload a new image.</p>
          </div>

          <button
            type="button"
            className="text-button"
            onClick={onClose}
            disabled={busy}
            aria-label="Close Media Library"
          >
            Close
          </button>
        </header>

        <div className="media-library-search">
          <input
            value={search}
            onChange={event => setSearch(event.target.value)}
            placeholder="Search filename or alt text"
            aria-label="Search Media Library"
          />

          <button
            type="button"
            className="secondary-button"
            onClick={() => void loadMedia(search)}
            disabled={busy}
          >
            Search
          </button>

          <button
            type="button"
            className="primary-button"
            onClick={() => setUploading(value => !value)}
            disabled={busy}
          >
            {uploading ? "Hide upload" : "Upload new"}
          </button>
        </div>

        {uploading && (
          <div className="media-library-upload">
            <input
              ref={fileInputRef}
              className="media-drop-input"
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              onChange={event =>
                acceptUploadFile(event.target.files?.[0] || null)
              }
            />

            <button
              type="button"
              className={`media-drop-zone ${dragActive ? "drag-active" : ""}`}
              onClick={() => fileInputRef.current?.click()}
              onDragEnter={event => {
                event.preventDefault();
                setDragActive(true);
              }}
              onDragOver={event => {
                event.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={event => {
                event.preventDefault();
                if (event.currentTarget === event.target) {
                  setDragActive(false);
                }
              }}
              onDrop={event => {
                event.preventDefault();
                setDragActive(false);
                acceptUploadFile(event.dataTransfer.files?.[0] || null);
              }}
            >
              <strong>
                {uploadFile
                  ? uploadFile.name
                  : "Drag and drop an image here"}
              </strong>

              <span>
                {uploadFile
                  ? `${Math.max(1, Math.round(uploadFile.size / 1024))} KB selected`
                  : "or click to browse from your computer"}
              </span>

              <small>JPEG, PNG, WebP or GIF · Maximum 8 MB</small>
            </button>

            {uploadFile && uploadPreviewUrl ? (
              <figure className="media-upload-preview">
                <img
                  src={uploadPreviewUrl}
                  alt={uploadAlt || uploadFile.name}
                />

                <figcaption>
                  <strong>{uploadFile.name}</strong>
                  <span>
                    Local preview — image is not uploaded yet
                  </span>
                </figcaption>
              </figure>
            ) : null}

            {uploadFile && (
              <button
                type="button"
                className="text-button danger-link"
                onClick={() => {
                  setUploadFile(null);
                  if (fileInputRef.current) {
                    fileInputRef.current.value = "";
                  }
                }}
                disabled={busy}
              >
                Remove selected image
              </button>
            )}

            <div className="media-upload-fields">
              <label>
                Alt text
                <input
                  value={uploadAlt}
                  onChange={event => setUploadAlt(event.target.value)}
                  maxLength={500}
                  placeholder="Describe the image for accessibility"
                />
              </label>

              <label>
                Caption
                <input
                  value={uploadCaption}
                  onChange={event => setUploadCaption(event.target.value)}
                  maxLength={2000}
                  placeholder="Optional image caption"
                />
              </label>
            </div>

            <button
              type="button"
              className="primary-button"
              onClick={() => void upload()}
              disabled={busy || !uploadFile}
            >
              {busy ? "Uploading…" : "Upload and insert"}
            </button>
          </div>
        )}

        {message && (
          <div className="form-error" role="alert">
            {message}
          </div>
        )}

        {busy && !uploading ? (
          <p className="media-library-status">Loading media…</p>
        ) : items.length ? (
          <div className="media-library-grid">
            {items.map(item => (
              <button
                type="button"
                className="media-library-item"
                key={item.id}
                onClick={() => void chooseAsset(item)}
              >
                <img
                  src={item.thumbnail_url || item.public_url}
                  alt={item.alt_text || ""}
                  loading="lazy"
                  decoding="async"
                />

                <span>{item.original_filename}</span>

                {item.width && item.height ? (
                  <small>
                    {item.width} × {item.height}
                  </small>
                ) : null}
              </button>
            ))}
          </div>
        ) : (
          <p className="media-library-status">
            No active media found. Upload a new image.
          </p>
        )}
      </section>
    </div>
  );
}
