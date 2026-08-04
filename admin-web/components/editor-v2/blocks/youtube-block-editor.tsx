"use client";

import type { CmsYoutubeBlock } from "@/lib/editor-v2/document-types";

type Props = {
  block: CmsYoutubeBlock;
  disabled?: boolean;
  onChange: (block: CmsYoutubeBlock) => void;
};

function extractYoutubeId(value: string): string {
  try {
    const url = new URL(value);

    if (url.hostname.includes("youtu.be")) {
      return url.pathname.replace("/", "");
    }

    if (url.hostname.includes("youtube.com")) {
      return (
        url.searchParams.get("v") ||
        url.pathname.split("/").filter(Boolean).at(-1) ||
        ""
      );
    }
  } catch {
    return "";
  }

  return "";
}

export function YouTubeBlockEditor({
  block,
  disabled = false,
  onChange,
}: Props) {
  const videoId = extractYoutubeId(block.url);

  return (
    <div className="editor-v2-youtube-editor">
      <label>
        <span>Video URL</span>
        <input
          value={block.url}
          disabled={disabled}
          placeholder="https://www.youtube.com/watch?v=..."
          onChange={event =>
            onChange({ ...block, url: event.target.value })
          }
        />
      </label>

      <label>
        <span>Video title</span>
        <input
          value={block.title}
          disabled={disabled}
          maxLength={240}
          placeholder="Accessible video title"
          onChange={event =>
            onChange({ ...block, title: event.target.value })
          }
        />
      </label>

      <div className="editor-v2-youtube-preview">
        {videoId ? (
          <a
            href={block.url}
            target="_blank"
            rel="noopener noreferrer"
            className="editor-v2-youtube-card"
            aria-label={
              block.title
                ? `Open YouTube video: ${block.title}`
                : "Open YouTube video"
            }
          >
            <img
              src={`https://img.youtube.com/vi/${videoId}/hqdefault.jpg`}
              alt={block.title || "YouTube video thumbnail"}
              loading="lazy"
              decoding="async"
            />

            <span className="editor-v2-youtube-play" aria-hidden="true">
              ▶
            </span>

            <span className="editor-v2-youtube-caption">
              <strong>{block.title || "YouTube video"}</strong>
              <small>Open on YouTube</small>
            </span>
          </a>
        ) : (
          <>
            <strong>Add a valid YouTube URL</strong>
            <span>The public preview will show a thumbnail and play button.</span>
          </>
        )}
      </div>
    </div>
  );
}
