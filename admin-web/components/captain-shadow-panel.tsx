import type {
  CaptainShadowState,
} from "@/lib/captain-shadow-api";

function value(input: string | null | undefined) {
  return input || "—";
}

export function CaptainShadowPanel({
  state,
}: {
  state: CaptainShadowState;
}) {
  const assessment = state.assessment;

  if (!state.available || !assessment) {
    return (
      <section className="captain-shadow-panel unavailable">
        <header>
          <div>
            <small>CAPTAIN AI SAFETY GATE</small>
            <h2>Captain Shadow Mode</h2>
          </div>
          <span className="captain-shadow-state error">
            FAIL-CLOSED
          </span>
        </header>

        <p>
          Captain assessment is currently unavailable. Signal
          approval and outbound delivery remain blocked by the
          production fail-closed safety gate.
        </p>
      </section>
    );
  }

  const decisionClass =
    assessment.decision === "APPROVE"
      ? "approve"
      : assessment.decision === "WAIT"
        ? "wait"
        : "reject";

  return (
    <section className="captain-shadow-panel">
      <header>
        <div>
          <small>CAPTAIN AI SAFETY GATE</small>
          <h2>Captain Shadow Mode</h2>
          <p>
            Live read-only XAUUSD assessment. No signal is created,
            published or delivered by this panel.
          </p>
        </div>

        <div className="captain-shadow-badges">
          <span className="captain-shadow-state active">
            ON · FAIL-CLOSED
          </span>
          <span
            className={`captain-shadow-decision ${decisionClass}`}
          >
            {assessment.decision}
            {assessment.direction !== "NONE"
              ? ` · ${assessment.direction}`
              : ""}
          </span>
        </div>
      </header>

      <div className="captain-shadow-grid">
        <article>
          <span>Confidence</span>
          <strong>{assessment.confidence}%</strong>
        </article>

        <article>
          <span>Live CMP</span>
          <strong>{value(assessment.live_cmp)}</strong>
        </article>

        <article>
          <span>Buy Base</span>
          <strong>{value(assessment.buy_base)}</strong>
        </article>

        <article>
          <span>Sell Base</span>
          <strong>{value(assessment.sell_base)}</strong>
        </article>

        <article>
          <span>Stop Loss</span>
          <strong>{value(assessment.stop_loss)}</strong>
        </article>

        <article>
          <span>5-Day Bias</span>
          <strong>{assessment.weekly?.bias || "—"}</strong>
        </article>

        <article>
          <span>Macro Bias</span>
          <strong>{assessment.macro_bias}</strong>
          <small>{assessment.macro_confidence}% confidence</small>
        </article>

        <article>
          <span>News Lock</span>
          <strong>
            {assessment.news_locked ? "ACTIVE" : "INACTIVE"}
          </strong>
        </article>
      </div>

      <div className="captain-shadow-targets">
        <strong>Captain Targets</strong>
        <div>
          {assessment.targets.length
            ? assessment.targets.map((target, index) => (
                <span key={`${target}-${index}`}>
                  T{index + 1}: {value(target)}
                </span>
              ))
            : <span>No targets approved.</span>}
        </div>
      </div>

      <div className="captain-shadow-reasons">
        <strong>Decision reasons</strong>
        {assessment.reasons.length ? (
          <ul>
            {assessment.reasons.map((reason, index) => (
              <li key={`${reason}-${index}`}>
                {reason}
              </li>
            ))}
          </ul>
        ) : (
          <p>No decision reason was returned.</p>
        )}
      </div>

      <footer>
        <span>
          Read only: {assessment.read_only ? "YES" : "NO"}
        </span>
        <span>
          Signal generated:{" "}
          {assessment.signal_generated ? "YES" : "NO"}
        </span>
        <span>
          Delivery started:{" "}
          {assessment.delivery_started ? "YES" : "NO"}
        </span>
      </footer>
    </section>
  );
}
