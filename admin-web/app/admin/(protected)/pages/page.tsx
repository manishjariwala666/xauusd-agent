import { ContentIndexPage } from "@/components/content-index-page";

export default function PagesPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  return <ContentIndexPage kind="pages" searchParams={searchParams} />;
}
