import type { Metadata } from "next";
import { ContentGrid } from "@/components/content-grid";
import { getContent } from "@/lib/api";

export const metadata: Metadata = { title: "Announcements", description: "Published VenusRealm platform and research updates." };
export const revalidate = 300;
export default async function AnnouncementsPage() { const items = await getContent("ANNOUNCEMENT", 40); return <section><header className="page-heading"><span className="eyebrow">PLATFORM UPDATES</span><h1>Announcements, clearly documented.</h1><p>Product, publishing and channel updates appear here only after they are publicly released.</p></header><ContentGrid items={items} empty="No announcements have been published yet." /></section>; }
