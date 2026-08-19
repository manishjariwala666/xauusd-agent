export type EditorV2Mode = "visual" | "source";

export type EditorV2Props = {
  value: string;
  onChange: (html: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
};

export type EditorV2MediaAsset = {
  id: number;
  public_url: string;
  thumbnail_url?: string | null;
  original_filename: string;
  alt_text?: string;
  caption?: string;
  width?: number;
  height?: number;
};

export type EditorV2ImageAlignment = "left" | "center" | "right" | "wide" | "full";

export type EditorV2ImageSettings = {
  src: string;
  alt: string;
  caption: string;
  width: number | null;
  height: number | null;
  alignment: EditorV2ImageAlignment;
  linkUrl: string;
  openInNewTab: boolean;
};
