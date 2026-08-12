import {
  SeoWorkspace,
} from "@/components/editor-v2/seo/seo-workspace";

export default function StudioSeoPage() {
  return (
    <main className="studio-v2-module-page">
      <header>
        <span className="section-kicker">
          SEARCH VISIBILITY
        </span>

        <h1>SEO Studio</h1>

        <p>
          Metadata, indexing controls, schema aur
          search preview manage karein.
        </p>
      </header>

      <SeoWorkspace />
    </main>
  );
}
