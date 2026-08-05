"use client";

import { useState } from "react";

import {
  AgentBuilderForm,
  type AgentBuilderSpec,
} from "./agent-builder-form";
import {
  BrainPreviewCard,
  type BrainPreview,
} from "./brain-preview-card";

export function AgentBuilderModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<BrainPreview | null>(null);

  if (!open) return null;

  async function generatePreview(spec: AgentBuilderSpec) {
    setBusy(true);
    setError("");
    setPreview(null);

    try {
      const csrfResponse = await fetch("/api/admin/auth/csrf", {
        cache: "no-store",
      });

      if (!csrfResponse.ok) {
        throw new Error("CSRF token could not be loaded.");
      }

      const csrfPayload = (await csrfResponse.json()) as {
        csrfToken?: string;
      };

      if (!csrfPayload.csrfToken) {
        throw new Error("CSRF token is missing.");
      }

      const response = await fetch(
        "/api/admin/agents/builder/preview",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrfPayload.csrfToken,
          },
          body: JSON.stringify(spec),
        },
      );

      const result = (await response.json()) as {
        preview?: BrainPreview;
        detail?: string;
        message?: string;
      };

      if (!response.ok || !result.preview) {
        throw new Error(
          result.detail ||
            result.message ||
            "Brain preview could not be generated.",
        );
      }

      setPreview(result.preview);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Agent Builder is temporarily unavailable.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="agent-builder-backdrop"
      role="presentation"
      onMouseDown={event => {
        if (event.target === event.currentTarget && !busy) {
          onClose();
        }
      }}
    >
      <section
        className="agent-builder-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="agent-builder-title"
      >
        <header className="agent-builder-header">
          <div>
            <span>VENUS AGENT OS</span>
            <h2 id="agent-builder-title">Create Agent Brain</h2>
            <p>
              Define an agent and generate its execution-locked safety
              contract preview.
            </p>
          </div>

          <button
            type="button"
            aria-label="Close Agent Builder"
            disabled={busy}
            onClick={onClose}
          >
            ×
          </button>
        </header>

        <div className="agent-builder-layout">
          <AgentBuilderForm busy={busy} onSubmit={generatePreview} />

          {error ? (
            <div className="form-error agent-builder-error" role="alert">
              {error}
            </div>
          ) : null}

          {preview ? <BrainPreviewCard preview={preview} /> : null}
        </div>
      </section>
    </div>
  );
}
