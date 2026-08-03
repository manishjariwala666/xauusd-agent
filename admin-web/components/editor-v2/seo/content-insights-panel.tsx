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

      <section className="studio-insight-card studio-link-audit-card">
        <header>
          <div>
            <span>LINK ANALYZER</span>
            <h2>{analysis.links.total}</h2>
          </div>

          <strong>
            {analysis.links.issueCount === 0
              ? "Clean"
              : `${analysis.links.issueCount} issues`}
          </strong>
        </header>

        <div className="studio-link-summary">
          <span>
            Internal <strong>{analysis.links.internal}</strong>
          </span>
          <span>
            External <strong>{analysis.links.external}</strong>
          </span>
          <span>
            Anchors <strong>{analysis.links.anchor}</strong>
          </span>
          <span>
            Invalid <strong>{analysis.links.invalid}</strong>
          </span>
        </div>

        {analysis.links.records.length > 0 ? (
          <div className="studio-link-records">
            {analysis.links.records.map(link => (
              <article
                key={link.id}
                className={
                  link.issues.length
                    ? "link-has-issues"
                    : "link-clean"
                }
              >
                <header>
                  <span className={`link-kind link-kind-${link.kind}`}>
                    {link.kind}
                  </span>

                  <small>{link.source}</small>
                </header>

                <strong>
                  {link.anchorText || "Missing anchor text"}
                </strong>

                <code title={link.url}>
                  {link.url || "Empty URL"}
                </code>

                <div className="studio-link-flags">
                  {link.nofollow ? <span>nofollow</span> : null}
                  {link.sponsored ? <span>sponsored</span> : null}
                  {link.ugc ? <span>ugc</span> : null}
                  {link.targetBlank ? <span>new tab</span> : null}
                </div>

                {link.issues.length > 0 ? (
                  <ul>
                    {link.issues.map(issue => (
                      <li key={issue}>
                        {issue
                          .replace(/-/g, " ")
                          .replace(
                            /^./,
                            value => value.toUpperCase(),
                          )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <small className="studio-link-clean-message">
                    No issues detected
                  </small>
                )}
              </article>
            ))}
          </div>
        ) : (
          <p className="studio-link-empty">
            No links detected in this article.
          </p>
        )}
      </section>

      <p className="studio-insights-note">
        Deterministic guidance hai. Search ranking
        ya trading outcome guarantee nahi hai.
      </p>
    </aside>
  );
}
