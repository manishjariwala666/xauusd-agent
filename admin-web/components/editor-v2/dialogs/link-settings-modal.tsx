"use client";

import { useEffect, useState } from "react";

export type LinkSettingsValue = {
  href: string;
  text: string;
  openInNewTab: boolean;
  nofollow: boolean;
  sponsored: boolean;
  ugc: boolean;
  underline: boolean;
  title: string;
  ariaLabel: string;
};

type Props = {
  open: boolean;
  initialValue: LinkSettingsValue;
  allowTextEditing: boolean;
  onClose: () => void;
  onSave: (value: LinkSettingsValue) => void;
  onRemove: () => void;
};

function classifyUrl(value: string): "internal" | "external" | "special" | "invalid" {
  const url = value.trim();

  if (!url) return "invalid";

  if (
    url.startsWith("/") ||
    url.startsWith("#") ||
    /^(?:https?:\/\/)?(?:www\.)?venusrealm\.net(?:\/|$)/i.test(url)
  ) {
    return "internal";
  }

  if (/^(mailto:|tel:)/i.test(url)) {
    return "special";
  }

  if (/^https?:\/\//i.test(url)) {
    return "external";
  }

  return "invalid";
}

export function LinkSettingsModal({
  open,
  initialValue,
  allowTextEditing,
  onClose,
  onSave,
  onRemove,
}: Props) {
  const [value, setValue] = useState(initialValue);

  useEffect(() => {
    if (!open) return;
    setValue(initialValue);
  }, [initialValue, open]);

  useEffect(() => {
    if (!open) return;

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };

    window.addEventListener("keydown", closeOnEscape);

    return () => {
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [onClose, open]);

  if (!open) return null;

  const urlKind = classifyUrl(value.href);
  const canSave =
    value.href.trim().length > 0 &&
    urlKind !== "invalid" &&
    (!allowTextEditing || value.text.trim().length > 0);

  function toggle(
    key:
      | "openInNewTab"
      | "nofollow"
      | "sponsored"
      | "ugc"
      | "underline",
  ) {
    setValue(current => ({
      ...current,
      [key]: !current[key],
    }));
  }

  return (
    <div
      className="editor-v2-link-modal-backdrop"
      role="presentation"
      onMouseDown={event => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="editor-v2-link-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="link-settings-title"
      >
        <header>
          <div>
            <span className="section-kicker">LINK SETTINGS</span>
            <h2 id="link-settings-title">
              Add or edit link
            </h2>
          </div>

          <button
            type="button"
            className="editor-v2-link-modal-close"
            onClick={onClose}
            aria-label="Close link settings"
          >
            ×
          </button>
        </header>

        <div className="editor-v2-link-modal-fields">
          <label>
            <span>URL</span>
            <input
              autoFocus
              value={value.href}
              placeholder="https://example.com or /internal-page"
              onChange={event =>
                setValue(current => ({
                  ...current,
                  href: event.target.value,
                }))
              }
            />

            <small className={`link-url-status status-${urlKind}`}>
              {urlKind === "internal"
                ? "Internal link"
                : urlKind === "external"
                  ? "External link"
                  : urlKind === "special"
                    ? "Email or telephone link"
                    : "Enter a valid URL, internal path or anchor"}
            </small>
          </label>

          {allowTextEditing ? (
            <label>
              <span>Link text</span>
              <input
                value={value.text}
                maxLength={240}
                placeholder="Visible link text"
                onChange={event =>
                  setValue(current => ({
                    ...current,
                    text: event.target.value,
                  }))
                }
              />
            </label>
          ) : null}

          <div className="editor-v2-link-option-grid">
            <label className="editor-v2-link-toggle">
              <input
                type="checkbox"
                checked={value.openInNewTab}
                onChange={() => toggle("openInNewTab")}
              />
              <span>
                <strong>Open in new tab</strong>
                <small>Adds secure external-tab attributes.</small>
              </span>
            </label>

            <label className="editor-v2-link-toggle">
              <input
                type="checkbox"
                checked={value.underline}
                onChange={() => toggle("underline")}
              />
              <span>
                <strong>Underline link</strong>
                <small>Recommended for accessibility.</small>
              </span>
            </label>

            <label className="editor-v2-link-toggle">
              <input
                type="checkbox"
                checked={value.nofollow}
                onChange={() => toggle("nofollow")}
              />
              <span>
                <strong>Nofollow</strong>
                <small>Do not pass normal ranking signals.</small>
              </span>
            </label>

            <label className="editor-v2-link-toggle">
              <input
                type="checkbox"
                checked={value.sponsored}
                onChange={() => toggle("sponsored")}
              />
              <span>
                <strong>Sponsored</strong>
                <small>Paid or affiliate relationship.</small>
              </span>
            </label>

            <label className="editor-v2-link-toggle">
              <input
                type="checkbox"
                checked={value.ugc}
                onChange={() => toggle("ugc")}
              />
              <span>
                <strong>UGC</strong>
                <small>User-generated content link.</small>
              </span>
            </label>
          </div>

          <div className="editor-v2-link-meta-grid">
            <label>
              <span>Title attribute</span>
              <input
                value={value.title}
                maxLength={240}
                placeholder="Optional tooltip"
                onChange={event =>
                  setValue(current => ({
                    ...current,
                    title: event.target.value,
                  }))
                }
              />
            </label>

            <label>
              <span>ARIA label</span>
              <input
                value={value.ariaLabel}
                maxLength={240}
                placeholder="Optional accessibility label"
                onChange={event =>
                  setValue(current => ({
                    ...current,
                    ariaLabel: event.target.value,
                  }))
                }
              />
            </label>
          </div>

          <div className="editor-v2-link-rel-preview">
            <span>SEO relationship</span>
            <code>
              {[
                value.openInNewTab ? "noopener noreferrer" : "",
                value.nofollow ? "nofollow" : "",
                value.sponsored ? "sponsored" : "",
                value.ugc ? "ugc" : "",
              ]
                .filter(Boolean)
                .join(" ") || "dofollow"}
            </code>
          </div>
        </div>

        <footer>
          <button
            type="button"
            className="editor-v2-link-remove"
            onClick={onRemove}
          >
            Remove link
          </button>

          <div>
            <button
              type="button"
              className="secondary-button"
              onClick={onClose}
            >
              Cancel
            </button>

            <button
              type="button"
              className="primary-button"
              disabled={!canSave}
              onClick={() => onSave(value)}
            >
              Save link
            </button>
          </div>
        </footer>
      </section>
    </div>
  );
}
