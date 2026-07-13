import { ContentGrid } from "@/components/content-grid";
import { getContent } from "@/lib/api";
export default async function AnnouncementsPage() { const items = await getContent("ANNOUNCEMENT", 40); return <section><div className="page-heading"><small>PLATFORM UPDATES</small><h1>Announcements</h1></div><ContentGrid items={items} empty="No announcements have been published yet." /></section>; }
