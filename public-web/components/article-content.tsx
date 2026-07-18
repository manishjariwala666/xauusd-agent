import type { ReactNode } from "react";

export type TocItem = { id: string; label: string; level: 2 | 3 };
type Block = { type: "heading" | "paragraph" | "quote" | "ul" | "ol"; text?: string; level?: 1 | 2 | 3; items?: string[]; id?: string };

function slugify(value: string) { return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""); }

export function parseArticle(body: string): { blocks: Block[]; toc: TocItem[] } {
  const lines = body.split("\n");
  const blocks: Block[] = [];
  const toc: TocItem[] = [];
  for (let index = 0; index < lines.length;) {
    const line = lines[index].trim();
    if (!line) { index += 1; continue; }
    const heading = /^(#{1,3})\s+(.+)$/.exec(line);
    if (heading) { const level = heading[1].length as 1 | 2 | 3; const text = heading[2].trim(); const id = slugify(text); blocks.push({ type: "heading", level, text, id }); if (level > 1) toc.push({ id, label: text, level: level as 2 | 3 }); index += 1; continue; }
    if (/^[*+-]\s+/.test(line)) { const items: string[] = []; while (index < lines.length && /^[*+-]\s+/.test(lines[index].trim())) { items.push(lines[index].trim().replace(/^[*+-]\s+/, "")); index += 1; } blocks.push({ type: "ul", items }); continue; }
    if (/^\d+[.)]\s+/.test(line)) { const items: string[] = []; while (index < lines.length && /^\d+[.)]\s+/.test(lines[index].trim())) { items.push(lines[index].trim().replace(/^\d+[.)]\s+/, "")); index += 1; } blocks.push({ type: "ol", items }); continue; }
    if (line.startsWith(">")) { blocks.push({ type: "quote", text: line.replace(/^>\s?/, "") }); index += 1; continue; }
    const paragraph = [line]; index += 1; while (index < lines.length && lines[index].trim() && !/^(#{1,3})\s+|^[*+-]\s+|^\d+[.)]\s+|^>/.test(lines[index].trim())) { paragraph.push(lines[index].trim()); index += 1; } blocks.push({ type: "paragraph", text: paragraph.join(" ") });
  }
  return { blocks, toc };
}

function inline(text = ""): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map((part, index) => part.startsWith("**") && part.endsWith("**") ? <strong key={index}>{part.slice(2, -2)}</strong> : part);
}

export function ArticleContent({ body }: { body: string }) {
  const { blocks } = parseArticle(body);
  return <div className="article-body">{blocks.map((block, index) => {
    if (block.type === "heading") { if (block.level === 1) return null; if (block.level === 2) return <h2 id={block.id} key={index}>{inline(block.text)}</h2>; return <h3 id={block.id} key={index}>{inline(block.text)}</h3>; }
    if (block.type === "quote") return <blockquote key={index}>{inline(block.text)}</blockquote>;
    if (block.type === "ul") return <ul key={index}>{block.items?.map((item, itemIndex) => <li key={itemIndex}>{inline(item)}</li>)}</ul>;
    if (block.type === "ol") return <ol key={index}>{block.items?.map((item, itemIndex) => <li key={itemIndex}>{inline(item)}</li>)}</ol>;
    return <p key={index}>{inline(block.text)}</p>;
  })}</div>;
}
