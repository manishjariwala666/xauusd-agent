"use client";

import {
  analyzeSeoDocument,
} from "@/lib/editor-v2/seo-analyzer";
import type {
  CmsDocument,
} from "@/lib/editor-v2/document-types";

export function ContentInsightsPanel({
  document,
}: {
  document: CmsDocument;
}) {
  const analysis = analyzeSeoDocument(document);

  const passedChecks = analysis.checks.filter(
    check => check.passed,
  ).length;

  return (
    <aside className="studio-insights-panel">
      <section className="studio-insight-card">
        <header>
          <div>
            <span>SEO SCORE</span>
            <h2>{analysis.seoScore}/100</h2>
          </div>

          <div
            className={`studio-score-badge ${
              analysis.seoScore >= 80
                ? "good"
                : analysis.seoScore >= 50
                  ? "warning"
                  : "poor"
            }`}
          >
            {analysis.seoScore >= 80
              ? "Good"
              : analysis.seoScore >= 50
                ? "Improve"
                : "Needs work"}
          </div>
        </header>

        <div className="studio-score-progress">
          <span
            style={{
              width: `${analysis.seoScore}%`,
            }}
          />
        </div>

        <ul>
          <li>
            H1: {analysis.headings.counts[1]}
          </li>
          <li>
            H2: {analysis.headings.counts[2]}
          </li>
          <li>
            H3: {analysis.headings.counts[3]}
          </li>
          <li>
            H4: {analysis.headings.counts[4]}
          </li>
          <li>
            H5: {analysis.headings.counts[5]}
          </li>
          <li>
            H6: {analysis.headings.counts[6]}
          </li>
          <li>
            Words: {analysis.wordCount}
          </li>
          <li>
            Reading time:{" "}
            {analysis.readingTimeMinutes} min
          </li>
        </ul>

        <a
          href="/studio-v2/seo"
          className="secondary-button"
        >
          Open SEO Studio
        </a>
      </section>

      <section className="studio-insight-card">
        <header>
          <div>
            <span>CONTENT CHECKER</span>
            <h2>
              {analysis.contentScore}/100
            </h2>
          </div>

          <strong>
            {passedChecks}/{analysis.checks.length}
          </strong>
        </header>

        <div className="studio-content-check-list">
          {analysis.checks.map(check => (
            <article
              key={check.id}
              className={
                check.passed
                  ? "check-passed"
                  : "check-warning"
              }
            >
              <span>
                {check.passed ? "✓" : "!"}
              </span>

              <div>
                <strong>{check.label}</strong>
                <small>{check.detail}</small>
              </div>
            </article>
          ))}
        </div>
      </section>

      <p className="studio-insights-note">
        Deterministic guidance hai. Search ranking
        ya trading outcome guarantee nahi hai.
      </p>
    </aside>
  );
}
