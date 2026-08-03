export type CmsDocumentStatus =
  | "draft"
  | "scheduled"
  | "published"
  | "trash";

export type CmsBlockType =
  | "paragraph"
  | "heading"
  | "image"
  | "gallery"
  | "table"
  | "quote"
  | "code"
  | "button"
  | "divider"
  | "accordion"
  | "youtube";

export type CmsBaseBlock = {
  id: string;
  type: CmsBlockType;
};

export type CmsParagraphBlock = CmsBaseBlock & {
  type: "paragraph";
  html: string;
};

export type CmsHeadingBlock = CmsBaseBlock & {
  type: "heading";
  level: 1 | 2 | 3 | 4 | 5 | 6;
  text: string;
};

export type CmsImageBlock = CmsBaseBlock & {
  type: "image";
  mediaId: number | null;
  src: string;
  alt: string;
  caption: string;
  width: number | null;
  height: number | null;
  alignment: "left" | "center" | "right" | "wide" | "full";
  linkUrl: string;
};

export type CmsGalleryBlock = CmsBaseBlock & {
  type: "gallery";
  mediaIds: number[];
  columns: 2 | 3 | 4 | 5;
  gap: number;
  lightbox: boolean;
  showCaptions: boolean;
};

export type CmsTableBlock = CmsBaseBlock & {
  type: "table";
  html: string;
};

export type CmsQuoteBlock = CmsBaseBlock & {
  type: "quote";
  html: string;
  citation: string;
};

export type CmsCodeBlock = CmsBaseBlock & {
  type: "code";
  language: string;
  code: string;
};

export type CmsButtonBlock = CmsBaseBlock & {
  type: "button";
  label: string;
  url: string;
  style: "primary" | "secondary" | "outline";
  alignment: "left" | "center" | "right";
};

export type CmsDividerBlock = CmsBaseBlock & {
  type: "divider";
  style: "solid" | "dashed" | "dots";
};

export type CmsAccordionItem = {
  id: string;
  title: string;
  html: string;
};

export type CmsAccordionBlock = CmsBaseBlock & {
  type: "accordion";
  items: CmsAccordionItem[];
};

export type CmsYoutubeBlock = CmsBaseBlock & {
  type: "youtube";
  url: string;
  title: string;
};

export type CmsBlock =
  | CmsParagraphBlock
  | CmsHeadingBlock
  | CmsImageBlock
  | CmsGalleryBlock
  | CmsTableBlock
  | CmsQuoteBlock
  | CmsCodeBlock
  | CmsButtonBlock
  | CmsDividerBlock
  | CmsAccordionBlock
  | CmsYoutubeBlock;

export type CmsSeoData = {
  metaTitle: string;
  metaDescription: string;
  focusKeyword: string;
  canonicalUrl: string;
  robotsIndex: boolean;
  robotsFollow: boolean;
  schemaJsonLd: Record<string, unknown> | null;
};

export type CmsSocialPlatform =
  | "whatsapp"
  | "telegram"
  | "facebook"
  | "x"
  | "linkedin"
  | "copy";

export type CmsSocialSharing = {
  enabled: boolean;
  platforms: CmsSocialPlatform[];
};

export type CmsRelatedPost = {
  id: string;
  title: string;
  url: string;
  excerpt: string;
};

export type CmsRelatedPosts = {
  enabled: boolean;
  heading: string;
  items: CmsRelatedPost[];
};

export type CmsDocument = {
  id: number | null;
  title: string;
  slug: string;
  excerpt: string;
  status: CmsDocumentStatus;
  categoryId: number | null;
  tags: string[];
  featuredMediaId: number | null;
  blocks: CmsBlock[];
  seo: CmsSeoData;
  socialSharing: CmsSocialSharing;
  relatedPosts: CmsRelatedPosts;
  scheduledAt: string | null;
  publishedAt: string | null;
  createdAt: string | null;
  updatedAt: string | null;
};
