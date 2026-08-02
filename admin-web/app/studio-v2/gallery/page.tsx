import {
  GalleryManagerWorkspace,
} from "@/components/editor-v2/gallery/gallery-manager-workspace";

export default function StudioGalleryPage() {
  return (
    <main className="studio-v2-module-page">
      <header>
        <span className="section-kicker">
          VISUAL CONTENT
        </span>

        <h1>Gallery Manager</h1>

        <p>
          Select approved media and create reusable
          responsive galleries.
        </p>
      </header>

      <GalleryManagerWorkspace />
    </main>
  );
}
