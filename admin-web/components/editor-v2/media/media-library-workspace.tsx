"use client";

import {
  useCallback,
  useEffect,
  useState,
  type DragEvent,
} from "react";

type MediaAsset = {
  id: number;
  public_url: string;
  thumbnail_url?: string | null;
  original_filename: string;
  alt_text?: string;
  caption?: string;
  mime_type?: string;
  size_bytes?: number;
  width?: number;
  height?: number;
  created_at?: string;
};

type MediaResponse = {
  items?: MediaAsset[];
  total?: number;
  message?: string;
  detail?: string;
};

async function csrfToken(): Promise<string> {
  const response = await fetch("/api/admin/auth/csrf", {
    cache: "no-store",
    credentials: "same-origin",
  });

  if (!response.ok) {
    throw new Error("CSRF initialization failed.");
  }

  const payload = (await response.json()) as {
    csrfToken?: string;
  };

  if (!payload.csrfToken) {
    throw new Error("CSRF token is missing.");
  }

  return payload.csrfToken;
}

function readableBytes(bytes?: number): string {
  if (!bytes) return "Unknown size";

  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function MediaLibraryWorkspace() {
  const [items, setItems] = useState<MediaAsset[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [altText, setAltText] = useState("");
  const [caption, setCaption] = useState("");
  const [message, setMessage] = useState("");

  const loadMedia = useCallback(async (term = "") => {
    setLoading(true);
    setMessage("");

    try {
      const response = await fetch(
        `/api/admin/media?page=1&page_size=48&state=active&search=${encodeURIComponent(term)}`,
        {
          cache: "no-store",
          credentials: "same-origin",
        },
      );

      const payload = (await response.json()) as MediaResponse;

      if (!response.ok) {
        setMessage(
          payload.detail ||
            payload.message ||
            "Media Library could not be loaded.",
        );
        return;
      }

      setItems(payload.items || []);
    } catch {
      setMessage("Media service is temporarily unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadMedia();
  }, [loadMedia]);

  function chooseFile(nextFile: File | null) {
    if (!nextFile) return;

    if (!nextFile.type.startsWith("image/")) {
      setMessage("Only supported image files can be uploaded.");
      return;
    }

    setFile(nextFile);
    setMessage("");
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    chooseFile(event.dataTransfer.files?.[0] || null);
  }

  async function uploadImage() {
    if (!file || uploading) return;

    setUploading(true);
    setMessage("");

    try {
      const token = await csrfToken();
      const formData = new FormData();

      formData.set("file", file);
      formData.set("alt_text", altText.trim());
      formData.set("caption", caption.trim());

      const response = await fetch("/api/admin/media/upload", {
        method: "POST",
        headers: {
          "X-CSRF-Token": token,
        },
        body: formData,
        credentials: "same-origin",
      });

      const payload = (await response.json()) as MediaAsset & {
        detail?: string;
        message?: string;
      };

      if (!response.ok) {
        setMessage(
          payload.detail ||
            payload.message ||
            "Image upload could not be completed.",
        );
        return;
      }

      setFile(null);
      setAltText("");
      setCaption("");
      setUploadOpen(false);
      setMessage("Image uploaded successfully.");

      await loadMedia(search);
    } catch {
      setMessage("Media upload is temporarily unavailable.");
    } finally {
      setUploading(false);
    }
  }

  async function trashMedia(item: MediaAsset) {
    const confirmed = window.confirm(
      `Move "${item.original_filename}" to Trash?`,
    );

    if (!confirmed) return;

    setMessage("");

    try {
      const token = await csrfToken();

      const response = await fetch(
        `/api/admin/media/${item.id}/trash`,
        {
          method: "POST",
          headers: {
            "X-CSRF-Token": token,
          },
          credentials: "same-origin",
        },
      );

      const payload = (await response.json()) as {
        detail?: string;
        message?: string;
      };

      if (!response.ok) {
        setMessage(
          payload.detail ||
            payload.message ||
            "Media could not be moved to Trash.",
        );
        return;
      }

      setMessage("Media moved to Trash.");
      await loadMedia(search);
    } catch {
      setMessage("Media service is temporarily unavailable.");
    }
  }

  async function copyUrl(url: string) {
    try {
      await navigator.clipboard.writeText(url);
      setMessage("Media URL copied.");
    } catch {
      setMessage("Media URL could not be copied.");
    }
  }

  return (
    <section className="studio-media-workspace">
      <div className="studio-media-toolbar">
        <div className="studio-media-search">
          <input
            value={search}
            onChange={event => setSearch(event.target.value)}
            placeholder="Search filename or alt text"
            aria-label="Search media"
          />

          <button
            type="button"
            className="secondary-button"
            disabled={loading}
            onClick={() => void loadMedia(search)}
          >
            Search
          </button>

          <button
            type="button"
            className="text-button"
            disabled={loading || !search}
            onClick={() => {
              setSearch("");
              void loadMedia("");
            }}
          >
            Clear
          </button>
        </div>

        <button
          type="button"
          className="primary-button"
          onClick={() => setUploadOpen(value => !value)}
        >
          {uploadOpen ? "Close upload" : "+ Upload Media"}
        </button>
      </div>

      {uploadOpen ? (
        <section className="studio-media-upload-panel">
          <div
            className={`studio-media-dropzone ${
              dragging ? "dragging" : ""
            }`}
            onDragEnter={event => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragOver={event => event.preventDefault()}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
          >
            <strong>
              {file ? file.name : "Drag and drop image here"}
            </strong>

            <span>
              JPEG, PNG, WebP or GIF. Maximum 8 MB.
            </span>

            <label className="secondary-button">
              Choose image
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif"
                hidden
                onChange={event =>
                  chooseFile(event.target.files?.[0] || null)
                }
              />
            </label>
          </div>

          <div className="studio-media-upload-fields">
            <label>
              <span>Alt text</span>
              <input
                value={altText}
                maxLength={500}
                onChange={event => setAltText(event.target.value)}
                placeholder="Describe the image for accessibility"
              />
            </label>

            <label>
              <span>Caption</span>
              <textarea
                value={caption}
                rows={3}
                maxLength={2000}
                onChange={event => setCaption(event.target.value)}
                placeholder="Optional caption"
              />
            </label>

            <button
              type="button"
              className="primary-button"
              disabled={!file || uploading}
              onClick={() => void uploadImage()}
            >
              {uploading ? "Uploading…" : "Upload image"}
            </button>
          </div>
        </section>
      ) : null}

      {message ? (
        <div className="studio-media-message" role="status">
          {message}
        </div>
      ) : null}

      {loading ? (
        <div className="studio-media-empty">
          Loading Media Library…
        </div>
      ) : items.length ? (
        <div className="studio-media-grid">
          {items.map(item => (
            <article className="studio-media-card" key={item.id}>
              <div className="studio-media-thumbnail">
                <span>Image unavailable</span>

                <img
                  src={item.thumbnail_url || item.public_url}
                  alt={item.alt_text || ""}
                  loading="lazy"
                  decoding="async"
                  onError={event => {
                    if (event.currentTarget.dataset.fallbackApplied) {
                      return;
                    }

                    event.currentTarget.dataset.fallbackApplied = "true";
                    event.currentTarget.src = "/media-fallback.svg";
                  }}
                />
              </div>

              <div className="studio-media-card-body">
                <strong title={item.original_filename}>
                  {item.original_filename}
                </strong>

                <small>
                  {item.width && item.height
                    ? `${item.width} × ${item.height}`
                    : "Unknown dimensions"}
                  {" · "}
                  {readableBytes(item.size_bytes)}
                </small>

                <span className={item.alt_text ? "" : "missing-alt"}>
                  {item.alt_text || "Missing alt text"}
                </span>

                <div className="studio-media-card-actions">
                  <a
                    href={item.public_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    View
                  </a>

                  <button
                    type="button"
                    onClick={() => void copyUrl(item.public_url)}
                  >
                    Copy URL
                  </button>

                  <button
                    type="button"
                    className="danger-link"
                    onClick={() => void trashMedia(item)}
                  >
                    Trash
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="studio-media-empty">
          <strong>No active media found</strong>
          <span>Upload an image to begin building the library.</span>
        </div>
      )}
    </section>
  );
}
