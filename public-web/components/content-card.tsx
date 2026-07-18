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
  const published = item.published_at || item.created_at;
  return (
    <Link className="content-card" href={contentHref(item)}>
      <div className="card-media">
        {item.image_url ? (
          <Image src={item.image_url} alt={`${item.title} featured image`} fill sizes="(max-width: 720px) 100vw, 33vw" />
        ) : (
          <div className="image-fallback"><span className="fallback-orbit" aria-hidden="true" /><span>VENUSREALM RESEARCH</span></div>
        )}
      </div>
      <div className="card-body"><div className="card-meta"><small>{item.category_title || item.content_type.replaceAll("_", " ")}</small>{published && <time dateTime={published}>{new Intl.DateTimeFormat("en", { day: "numeric", month: "short", year: "numeric" }).format(new Date(published))}</time>}</div><h3>{item.title}</h3><p>{item.excerpt || "Read the complete market update."}</p><span>Read analysis <span aria-hidden="true">→</span></span></div>
    </Link>
  );
}
