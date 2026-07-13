import type { ContentItem } from "@/lib/types";
import { ContentCard } from "./content-card";

export function ContentGrid({ items, empty = "No published posts are available yet." }: { items: ContentItem[]; empty?: string }) {
  if (!items.length) return <div className="empty-state">{empty}</div>;
  return <div className="content-grid">{items.map((item) => <ContentCard item={item} key={item.id} />)}</div>;
}
