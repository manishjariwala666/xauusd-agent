import { ContentIndexPage } from "@/components/content-index-page";

export default function StudioV2PostsPage({
  searchParams,
}: {
  searchParams: Promise<
    Record<string, string | string[] | undefined>
  >;
}) {
  return (
    <ContentIndexPage
      kind="posts"
      searchParams={searchParams}
      basePath="/studio-v2/posts"
      readOnly
    />
  );
}
