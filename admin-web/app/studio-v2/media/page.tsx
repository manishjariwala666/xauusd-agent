import {
  MediaLibraryWorkspace,
} from "@/components/editor-v2/media/media-library-workspace";

export default function StudioMediaPage() {
  return (
    <main className="studio-v2-module-page">
      <header className="studio-v2-module-heading">
        <div>
          <span className="section-kicker">CONTENT ASSETS</span>
          <h1>Media Library V2</h1>
          <p>
            Upload, organize, search and safely reuse images
            across content and galleries.
          </p>
        </div>
      </header>

      <MediaLibraryWorkspace />
    </main>
  );
}
