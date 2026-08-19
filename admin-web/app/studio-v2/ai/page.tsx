import { AIBlogDraftGenerator } from "@/components/ai-blog-draft-generator";

export default function StudioAiPage() {
  return (
    <main className="studio-v2-module-page">
      <span className="section-kicker">AI ASSISTANCE</span>

      <h1>AI Content Tools</h1>

      <p>
        Plan and generate review-only content drafts with AI.
        Publishing remains locked and requires a separate administrator-controlled workflow.
      </p>

      <section className="studio-panel">
        <AIBlogDraftGenerator />
      </section>
    </main>
  );
}
