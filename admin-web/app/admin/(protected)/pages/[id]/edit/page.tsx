import { ContentEditorPage } from "@/components/content-editor-page";

export default async function EditPagePage({ params }: { params: Promise<{ id: string }> }) {
  return <ContentEditorPage kind="pages" id={(await params).id} />;
}
