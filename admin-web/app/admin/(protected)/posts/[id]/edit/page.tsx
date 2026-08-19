import { ContentEditorPage } from "@/components/content-editor-page";

export default async function EditPostPage({ params }: { params: Promise<{ id: string }> }) {
  return <ContentEditorPage kind="posts" id={(await params).id} />;
}
