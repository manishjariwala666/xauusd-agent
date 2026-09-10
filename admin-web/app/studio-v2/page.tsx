import {
  PublishedFeaturedImageSync,
} from "@/components/editor-v2/core/published-featured-image-sync";
import {
  StudioWorkspace,
} from "@/components/editor-v2/core/studio-workspace";

export default function StudioV2Page() {
  return (
    <>
      <PublishedFeaturedImageSync />
      <StudioWorkspace />
    </>
  );
}
