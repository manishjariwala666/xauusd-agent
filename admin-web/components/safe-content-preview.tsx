import type { ReactNode } from "react";

function clean(value: string) {
  return value.replace(/<script[\s\S]*?<\/script>/gi, "").replace(/<style[\s\S]*?<\/style>/gi, "")
    .replace(/<br\s*\/?>/gi, "\n").replace(/<\/(h[1-3]|p|li|blockquote|ul|ol)>/gi, "\n")
    .replace(/<h1[^>]*>/gi, "# ").replace(/<h2[^>]*>/gi, "## ").replace(/<h3[^>]*>/gi, "### ")
    .replace(/<li[^>]*>/gi, "- ").replace(/<blockquote[^>]*>/gi, "> ").replace(/<[^>]+>/g, "")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&").replace(/&quot;/g, "\"").trim();
}

function inline(text: string): ReactNode[] {
  const output: ReactNode[] = [];
  const pattern = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g;
  let cursor = 0; let match: RegExpExecArray | null;
  while ((match = pattern.exec(text))) {
    output.push(text.slice(cursor, match.index));
    output.push(<a href={match[2]} target="_blank" rel="noreferrer" key={`${match.index}-${match[2]}`}>{match[1]}</a>);
    cursor = match.index + match[0].length;
  }
  output.push(text.slice(cursor));
  return output;
}

export function SafeContentPreview({ body, title }: { body: string; title?: string }) {
  const lines = clean(body).split(/\n+/).map(line => line.trim()).filter(Boolean);
  return <article className="article-preview">
    {title && <h1>{title}</h1>}
    {lines.length ? lines.map((line, index) => {
      if (line.startsWith("### ")) return <h3 key={index}>{inline(line.slice(4))}</h3>;
      if (line.startsWith("## ")) return <h2 key={index}>{inline(line.slice(3))}</h2>;
      if (line.startsWith("# ")) return <h1 key={index}>{inline(line.slice(2))}</h1>;
      if (line.startsWith("> ")) return <blockquote key={index}>{inline(line.slice(2))}</blockquote>;
      if (/^[-*]\s/.test(line)) return <ul key={index}><li>{inline(line.slice(2))}</li></ul>;
      if (/^\d+\.\s/.test(line)) return <ol key={index}><li>{inline(line.replace(/^\d+\.\s/, ""))}</li></ol>;
      return <p key={index}>{inline(line)}</p>;
    }) : <p className="preview-empty">Article preview appears here as you write.</p>}
  </article>;
}
