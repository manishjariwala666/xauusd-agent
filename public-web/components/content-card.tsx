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
  const fallbackLabel = item.content_type === "AI_BLOG" ? "AI-ASSISTED RESEARCH" : "VENUSREALM RESEARCH";
  return (
    <Link className="content-card" href={contentHref(item)}>
      <div className={`card-media${item.image_url ? "" : " card-media-fallback"}`}>
        {item.image_url ? (
          <Image src={item.image_url} alt={`${item.title} featured image`} fill sizes="(max-width: 720px) 100vw, 33vw" />
        ) : (
          <>
            <Image className="fallback-research-image" src="/images/home/venusrealm-gold-desk-hero.png" alt="VenusRealm gold research desk" fill sizes="(max-width: 720px) 100vw, 33vw" />
            <span className="fallback-research-shade" aria-hidden="true" />
            <div className="fallback-research-label"><small>{fallbackLabel}</small><strong>Gold intelligence, visually presented.</strong></div>
          </>
        )}
      </div>
      <div className="card-body"><div className="card-meta"><small>{item.category_title || item.content_type.replaceAll("_", " ")}</small>{published && <time dateTime={published}>{new Intl.DateTimeFormat("en", { day: "numeric", month: "short", year: "numeric" }).format(new Date(published))}</time>}</div><h3>{item.title}</h3><p>{item.excerpt || "Read the complete market update."}</p><span>Read analysis <span aria-hidden="true">→</span></span></div>
    </Link>
  );
}
