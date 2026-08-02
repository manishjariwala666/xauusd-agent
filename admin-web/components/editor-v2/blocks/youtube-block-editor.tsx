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
          <>
            <strong>{block.title || "YouTube video ready"}</strong>
            <span>Video ID: {videoId}</span>
          </>
        ) : (
          <>
            <strong>Add a valid YouTube URL</strong>
            <span>The public embed will be generated safely.</span>
          </>
        )}
      </div>
    </div>
  );
}
