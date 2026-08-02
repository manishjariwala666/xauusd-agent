import type {
  CmsAccordionBlock,
  CmsBlock,
  CmsBlockType,
  CmsButtonBlock,
  CmsCodeBlock,
  CmsDividerBlock,
  CmsGalleryBlock,
  CmsHeadingBlock,
  CmsParagraphBlock,
  CmsQuoteBlock,
  CmsTableBlock,
  CmsYoutubeBlock,
} from "./document-types";
import { createBlockId, createImageBlock } from "./document-store";

export function createBlock(type: CmsBlockType): CmsBlock {
  switch (type) {
    case "paragraph":
      return {
        id: createBlockId("paragraph"),
        type: "paragraph",
        html: "<p></p>",
      } satisfies CmsParagraphBlock;

    case "heading":
      return {
        id: createBlockId("heading"),
        type: "heading",
        level: 2,
        text: "",
      } satisfies CmsHeadingBlock;

    case "image":
      return createImageBlock({ src: "" });

    case "gallery":
      return {
        id: createBlockId("gallery"),
        type: "gallery",
        mediaIds: [],
        columns: 3,
        gap: 16,
        lightbox: true,
        showCaptions: true,
      } satisfies CmsGalleryBlock;

    case "table":
      return {
        id: createBlockId("table"),
        type: "table",
        html: `
          <table>
            <thead>
              <tr><th>Column 1</th><th>Column 2</th></tr>
            </thead>
            <tbody>
              <tr><td></td><td></td></tr>
            </tbody>
          </table>
        `.trim(),
      } satisfies CmsTableBlock;

    case "quote":
      return {
        id: createBlockId("quote"),
        type: "quote",
        html: "<p></p>",
        citation: "",
      } satisfies CmsQuoteBlock;

    case "code":
      return {
        id: createBlockId("code"),
        type: "code",
        language: "text",
        code: "",
      } satisfies CmsCodeBlock;

    case "button":
      return {
        id: createBlockId("button"),
        type: "button",
        label: "Learn more",
        url: "",
        style: "primary",
        alignment: "left",
      } satisfies CmsButtonBlock;

    case "divider":
      return {
        id: createBlockId("divider"),
        type: "divider",
        style: "solid",
      } satisfies CmsDividerBlock;

    case "accordion":
      return {
        id: createBlockId("accordion"),
        type: "accordion",
        items: [
          {
            id: createBlockId("accordion-item"),
            title: "Accordion title",
            html: "<p>Accordion content</p>",
          },
        ],
      } satisfies CmsAccordionBlock;

    case "youtube":
      return {
        id: createBlockId("youtube"),
        type: "youtube",
        url: "",
        title: "",
      } satisfies CmsYoutubeBlock;
  }
}
