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
          <li>H1: {analysis.headings.counts[1]}</li>
          <li>H2: {analysis.headings.counts[2]}</li>
          <li>H3: {analysis.headings.counts[3]}</li>
          <li>H4: {analysis.headings.counts[4]}</li>
          <li>H5: {analysis.headings.counts[5]}</li>
          <li>H6: {analysis.headings.counts[6]}</li>
          <li>Words: {analysis.wordCount}</li>
          <li>
            Reading time:{" "}
            {analysis.readingTimeMinutes} min
          </li>
        </ul>

        <div className="studio-score-breakdown">
          <h3>Score Breakdown</h3>

          {analysis.scoreBreakdown.map(item => (
            <div
              key={item.id}
              className="studio-score-row"
            >
              <span>{item.label}</span>

              <strong
                className={
                  item.passed
                    ? "score-good"
                    : "score-bad"
                }
              >
                +{item.earned}/{item.points}
              </strong>
            </div>
          ))}
        </div>

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
            <h2>{analysis.contentScore}/100</h2>
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
              <span>{check.passed ? "✓" : "!"}</span>

              <div>
                <strong>{check.label}</strong>
                <small>{check.detail}</small>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="studio-insight-card studio-keyword-card">
        <header>
          <div>
            <span>KEYWORD DENSITY</span>
            <h2>
              {analysis.keywordAnalysis.density}%
            </h2>
          </div>

          <strong>
            {analysis.keywordAnalysis.occurrences}{" "}
            matches
          </strong>
        </header>

        <div className="studio-keyword-grid">
          <div>
            <span>Keyword</span>
            <strong>
              {analysis.keywordAnalysis.keyword ||
                "Not set"}
            </strong>
          </div>

          <div>
            <span>Title</span>
            <strong>
              {analysis.keywordAnalysis.inTitle
                ? "✓"
                : "✗"}
            </strong>
          </div>

          <div>
            <span>Meta title</span>
            <strong>
              {analysis.keywordAnalysis.inMetaTitle
                ? "✓"
                : "✗"}
            </strong>
          </div>

          <div>
            <span>Meta description</span>
            <strong>
              {analysis.keywordAnalysis
                .inMetaDescription
                ? "✓"
                : "✗"}
            </strong>
          </div>

          <div>
            <span>Slug</span>
            <strong>
              {analysis.keywordAnalysis.inSlug
                ? "✓"
                : "✗"}
            </strong>
          </div>

          <div>
            <span>H1</span>
            <strong>
              {analysis.keywordAnalysis.inH1
                ? "✓"
                : "✗"}
            </strong>
          </div>

          <div>
            <span>H2 headings</span>
            <strong>
              {analysis.keywordAnalysis.h2Count}
            </strong>
          </div>

          <div>
            <span>H3 headings</span>
            <strong>
              {analysis.keywordAnalysis.h3Count}
            </strong>
          </div>
        </div>
      </section>

      <section className="studio-insight-card studio-readability-card">
        <header>
          <div>
            <span>READABILITY</span>
            <h2>{analysis.readability.score}/100</h2>
          </div>

          <strong>{analysis.readability.label}</strong>
        </header>

        <div className="studio-readability-grid">
          <div>
            <span>Sentences</span>
            <strong>
              {analysis.readability.sentenceCount}
            </strong>
          </div>

          <div>
            <span>Paragraphs</span>
            <strong>
              {analysis.readability.paragraphCount}
            </strong>
          </div>

          <div>
            <span>Avg. sentence</span>
            <strong>
              {analysis.readability
                .averageSentenceWords}{" "}
              words
            </strong>
          </div>

          <div>
            <span>Long sentences</span>
            <strong>
              {analysis.readability.longSentenceCount}
            </strong>
          </div>

          <div>
            <span>Long paragraphs</span>
            <strong>
              {analysis.readability.longParagraphCount}
            </strong>
          </div>
        </div>
      </section>

      <section className="studio-insight-card studio-publish-checklist-card">
        <header>
          <div>
            <span>PUBLISH CHECKLIST</span>
            <h2>
              {analysis.publishChecklist.passed}/
              {analysis.publishChecklist.total}
            </h2>
          </div>

          <strong>
            {analysis.publishChecklist.ready
              ? "Publish ready"
              : "Needs attention"}
          </strong>
        </header>

        <div className="studio-publish-checklist">
          {analysis.publishChecklist.items.map(item => (
            <article
              key={item.id}
              className={
                item.passed
                  ? "publish-check-passed"
                  : item.required
                    ? "publish-check-required"
                    : "publish-check-optional"
              }
            >
              <span>{item.passed ? "✓" : "!"}</span>

              <div>
                <strong>{item.label}</strong>
                <small>{item.detail}</small>
              </div>

              <em>
                {item.required
                  ? "Required"
                  : "Optional"}
              </em>
            </article>
          ))}
        </div>
      </section>

      <section className="studio-insight-card studio-image-seo-card">
        <header>
          <div>
            <span>IMAGE SEO</span>
            <h2>{analysis.imageSeo.score}/100</h2>
          </div>

          <strong>
            {analysis.imageSeo.total} images
          </strong>
        </header>

        <div className="studio-image-seo-grid">
          <div>
            <span>Missing ALT</span>
            <strong>
              {analysis.imageSeo.missingAlt}
            </strong>
          </div>

          <div>
            <span>Missing Source</span>
            <strong>
              {analysis.imageSeo.missingSource}
            </strong>
          </div>

          <div>
            <span>Missing Dimensions</span>
            <strong>
              {analysis.imageSeo.missingDimensions}
            </strong>
          </div>

          <div>
            <span>Missing Caption</span>
            <strong>
              {analysis.imageSeo.missingCaption}
            </strong>
          </div>

          <div>
            <span>External Images</span>
            <strong>
              {analysis.imageSeo.externalSources}
            </strong>
          </div>

          <div>
            <span>Large Images</span>
            <strong>
              {analysis.imageSeo.largeDimensions}
            </strong>
          </div>
        </div>

        {analysis.imageSeo.records.length > 0 ? (
          <div className="studio-image-records">
            {analysis.imageSeo.records.map(image => (
              <article
                key={image.id}
                className={
                  image.issues.length > 0
                    ? "image-has-issues"
                    : "image-clean"
                }
              >
                <header>
                  <strong>
                    {image.alt || "Missing ALT text"}
                  </strong>

                  <small>
                    {image.width && image.height
                      ? `${image.width} × ${image.height}`
                      : "Dimensions missing"}
                  </small>
                </header>

                <code title={image.src}>
                  {image.src || "Missing image source"}
                </code>

                {image.caption ? (
                  <p>{image.caption}</p>
                ) : null}

                {image.issues.length > 0 ? (
                  <ul>
                    {image.issues.map(issue => (
                      <li key={issue}>{issue}</li>
                    ))}
                  </ul>
                ) : (
                  <small className="studio-image-clean-message">
                    No image SEO issues detected
                  </small>
                )}
              </article>
            ))}
          </div>
        ) : (
          <p className="studio-image-empty">
            No image blocks detected in this article.
          </p>
        )}
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
            Internal{" "}
            <strong>
              {analysis.links.internal}
            </strong>
          </span>

          <span>
            External{" "}
            <strong>
              {analysis.links.external}
            </strong>
          </span>

          <span>
            Anchors{" "}
            <strong>
              {analysis.links.anchor}
            </strong>
          </span>

          <span>
            Invalid{" "}
            <strong>
              {analysis.links.invalid}
            </strong>
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
                  <span
                    className={`link-kind link-kind-${link.kind}`}
                  >
                    {link.kind}
                  </span>

                  <small>{link.source}</small>
                </header>

                <strong>
                  {link.anchorText ||
                    "Missing anchor text"}
                </strong>

                <code title={link.url}>
                  {link.url || "Empty URL"}
                </code>

                <div className="studio-link-flags">
                  {link.nofollow ? (
                    <span>nofollow</span>
                  ) : null}

                  {link.sponsored ? (
                    <span>sponsored</span>
                  ) : null}

                  {link.ugc ? (
                    <span>ugc</span>
                  ) : null}

                  {link.targetBlank ? (
                    <span>new tab</span>
                  ) : null}
                </div>

                {link.issues.length > 0 ? (
                  <ul>
                    {link.issues.map(issue => (
                      <li key={issue}>
                        {issue
                          .replace(/-/g, " ")
                          .replace(
                            /^./,
                            value =>
                              value.toUpperCase(),
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