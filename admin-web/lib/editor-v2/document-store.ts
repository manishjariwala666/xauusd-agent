import type {
  CmsBlock,
  CmsDocument,
  CmsImageBlock,
  CmsParagraphBlock,
} from "./document-types";

export function createBlockId(prefix = "block"): string {
  return `${prefix}-${crypto.randomUUID()}`;
}

export function createEmptyParagraphBlock(): CmsParagraphBlock {
  return {
    id: createBlockId("paragraph"),
    type: "paragraph",
    html: "<p></p>",
  };
}

export function createEmptyDocument(): CmsDocument {
  return {
    id: null,
    title: "",
    slug: "",
    excerpt: "",
    status: "draft",
    categoryId: null,
    tags: [],
    featuredMediaId: null,
    blocks: [createEmptyParagraphBlock()],
    seo: {
      metaTitle: "",
      metaDescription: "",
      focusKeyword: "",
      canonicalUrl: "",
      robotsIndex: false,
      robotsFollow: false,
      schemaJsonLd: null,
    },
    scheduledAt: null,
    publishedAt: null,
    createdAt: null,
    updatedAt: null,
  };
}

export function addBlock(
  document: CmsDocument,
  block: CmsBlock,
  afterBlockId?: string,
): CmsDocument {
  const blocks = [...document.blocks];

  if (!afterBlockId) {
    blocks.push(block);
    return { ...document, blocks };
  }

  const index = blocks.findIndex(block => block.id === afterBlockId);

  if (index === -1) {
    blocks.push(block);
  } else {
    blocks.splice(index + 1, 0, block);
  }

  return { ...document, blocks };
}

export function updateBlock<T extends CmsBlock>(
  document: CmsDocument,
  blockId: string,
  updater: (block: T) => T,
): CmsDocument {
  return {
    ...document,
    blocks: document.blocks.map(block =>
      block.id === blockId ? updater(block as T) : block,
    ),
  };
}

export function removeBlock(
  document: CmsDocument,
  blockId: string,
): CmsDocument {
  const blocks = document.blocks.filter(block => block.id !== blockId);

  return {
    ...document,
    blocks: blocks.length ? blocks : [createEmptyParagraphBlock()],
  };
}

export function duplicateBlock(
  document: CmsDocument,
  blockId: string,
): CmsDocument {
  const index = document.blocks.findIndex(block => block.id === blockId);

  if (index === -1) return document;

  const source = document.blocks[index];
  const duplicated = {
    ...structuredClone(source),
    id: createBlockId(source.type),
  } as CmsBlock;

  const blocks = [...document.blocks];
  blocks.splice(index + 1, 0, duplicated);

  return { ...document, blocks };
}

export function moveBlock(
  document: CmsDocument,
  blockId: string,
  direction: "up" | "down",
): CmsDocument {
  const index = document.blocks.findIndex(block => block.id === blockId);

  if (index === -1) return document;

  const targetIndex = direction === "up" ? index - 1 : index + 1;

  if (targetIndex < 0 || targetIndex >= document.blocks.length) {
    return document;
  }

  const blocks = [...document.blocks];
  [blocks[index], blocks[targetIndex]] = [
    blocks[targetIndex],
    blocks[index],
  ];

  return { ...document, blocks };
}

export function reorderBlocks(
  document: CmsDocument,
  orderedIds: string[],
): CmsDocument {
  const blockMap = new Map(
    document.blocks.map(block => [block.id, block]),
  );

  const ordered = orderedIds
    .map(id => blockMap.get(id))
    .filter((block): block is CmsBlock => Boolean(block));

  const missing = document.blocks.filter(
    block => !orderedIds.includes(block.id),
  );

  return {
    ...document,
    blocks: [...ordered, ...missing],
  };
}

export function createImageBlock(
  input: Partial<CmsImageBlock> & Pick<CmsImageBlock, "src">,
): CmsImageBlock {
  return {
    id: createBlockId("image"),
    type: "image",
    mediaId: input.mediaId ?? null,
    src: input.src,
    alt: input.alt ?? "",
    caption: input.caption ?? "",
    width: input.width ?? null,
    height: input.height ?? null,
    alignment: input.alignment ?? "center",
    linkUrl: input.linkUrl ?? "",
  };
}
