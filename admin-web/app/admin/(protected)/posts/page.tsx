import { ContentIndexPage } from "@/components/content-index-page";

export default function PostsPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  return <ContentIndexPage kind="posts" searchParams={searchParams} />;
}
