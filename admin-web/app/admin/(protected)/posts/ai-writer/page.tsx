import Link from "next/link";
import { AIBlogDraftGenerator } from "@/components/ai-blog-draft-generator";

export default function AIWriterPage() {
  return (
    <main className="ai-content-studio-page">
      <header className="ai-content-studio-heading">
        <div>
          <span className="eyebrow">VENUSREALM AI CONTENT ENGINE</span>
          <h1>AI Content Studio</h1>
          <p>
            Plan, review and generate one complete draft. Nothing is published
            automatically.
          </p>
        </div>
        <Link href="/admin/posts" className="secondary-button">
          ← Back to Blog Studio
        </Link>
      </header>
      <AIBlogDraftGenerator />
    </main>
  );
}
