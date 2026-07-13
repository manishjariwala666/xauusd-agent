import Image from "next/image";
import Link from "next/link";
import type { ContentItem } from "@/lib/types";

export function contentHref(item: ContentItem): string {
  if (item.content_type === "ANNOUNCEMENT") return `/announcements/${item.slug}`;
  if (item.content_type === "PAGE") return `/page/${item.slug}`;
  if (item.content_type === "SIGNAL_POST") return `/signals#${item.slug}`;
  return `/blog/${item.slug}`;
}

export function ContentCard({ item }: { item: ContentItem }) {
  return (
    <Link className="content-card" href={contentHref(item)}>
      <div className="card-media">
        {item.image_url ? (
          <Image src={item.image_url} alt={`${item.title} featured image`} fill sizes="(max-width: 720px) 100vw, 33vw" />
        ) : (
          <div className="image-fallback"><span>MARKET INTELLIGENCE</span><b>{item.title}</b></div>
        )}
      </div>
      <div className="card-body"><small>{item.category_title || item.content_type.replaceAll("_", " ")}</small><h3>{item.title}</h3><p>{item.excerpt || "Read the complete market update."}</p><span>Read article →</span></div>
    </Link>
  );
}
