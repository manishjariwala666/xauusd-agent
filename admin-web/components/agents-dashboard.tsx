import type {
  AgentDashboardRecord,
  AgentsDashboardPayload,
} from "@/lib/agents-api";

function humanize(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function riskClass(risk: AgentDashboardRecord["default_risk"]): string {
  return `agent-risk agent-risk-${risk.toLowerCase().replaceAll("_", "-")}`;
}

function ActionList({
  title,
  items,
  emptyLabel,
}: {
  title: string;
  items: string[];
  emptyLabel: string;
}) {
  return (
    <section className="agent-action-group">
      <h3>{title}</h3>
      {items.length ? (
        <ul>
          {items.map((item) => (
            <li key={item}>{humanize(item)}</li>
          ))}
        </ul>
      ) : (
        <p>{emptyLabel}</p>
      )}
    </section>
  );
}

function AgentCard({ agent }: { agent: AgentDashboardRecord }) {
  return (
    <article className="agent-card">
      <header className="agent-card-header">
        <div>
          <small>{agent.agent_key}</small>
          <h2>{agent.short_name}</h2>
          <p>{agent.official_name}</p>
        </div>

        <div className="agent-card-badges">
          <span className={riskClass(agent.default_risk)}>
            {humanize(agent.default_risk)}
          </span>
          <span
            className={
              agent.brain_configured
                ? "agent-brain agent-brain-ready"
                : "agent-brain agent-brain-missing"
            }
          >
            {agent.brain_configured ? "Brain ready" : "Brain missing"}
          </span>
        </div>
      </header>

      <p className="agent-purpose">{agent.purpose}</p>

      <dl className="agent-summary">
        <div>
          <dt>Direct run</dt>
          <dd>
            {agent.run_action
              ? humanize(agent.run_action)
              : "Not registered"}
          </dd>
        </div>
        <div>
          <dt>Aliases</dt>
          <dd>
            {agent.aliases.length
              ? agent.aliases.join(", ")
              : "None"}
          </dd>
        </div>
        <div>
          <dt>Output fields</dt>
          <dd>{agent.output_schema.length}</dd>
        </div>
      </dl>

      <div className="agent-action-grid">
        <ActionList
          title="Automatic"
          items={agent.automatic_actions}
          emptyLabel="No automatic actions."
        />
        <ActionList
          title="Approval required"
          items={agent.approval_required_actions}
          emptyLabel="No approval-gated actions."
        />
        <ActionList
          title="Forbidden"
          items={agent.forbidden_actions}
          emptyLabel="No forbidden actions listed."
        />
      </div>

      <footer className="agent-card-footer">
        <span>Read-only dashboard</span>
        <button type="button" disabled>
          Controls coming later
        </button>
      </footer>
    </article>
  );
}

export function AgentsDashboard({
  data,
}: {
  data: AgentsDashboardPayload;
}) {
  const configured = data.items.filter(
    (agent) => agent.brain_configured,
  ).length;
  const highRisk = data.items.filter(
    (agent) =>
      agent.default_risk === "HIGH" ||
      agent.default_risk === "CRITICAL",
  ).length;
  const approvalGated = data.items.filter(
    (agent) => agent.approval_required_actions.length > 0,
  ).length;

  return (
    <>
      <section className="page-heading agents-heading">
        <small className="eyebrow">AGENT OPERATIONS</small>
        <h1>VenusRealm Agents</h1>
        <p>
          Mobile-ready overview of registered agent brains,
          permissions and safety boundaries. Operational controls
          remain disabled in this read-only phase.
        </p>
      </section>

      <section
        className="kpi-grid agent-kpi-grid"
        aria-label="Agent dashboard summary"
      >
        <article className="kpi-card">
          <small>Registered agents</small>
          <strong>{data.count}</strong>
          <span>Registry total</span>
        </article>
        <article className="kpi-card">
          <small>Brains configured</small>
          <strong>{configured}</strong>
          <span>Machine-readable contracts</span>
        </article>
        <article className="kpi-card">
          <small>High-risk agents</small>
          <strong>{highRisk}</strong>
          <span>Extra safeguards</span>
        </article>
        <article className="kpi-card">
          <small>Approval gated</small>
          <strong>{approvalGated}</strong>
          <span>Owner decision required</span>
        </article>
      </section>

      <aside className="agents-readonly-notice" role="status">
        <strong>Read-only safety mode</strong>
        <p>
          No agent can be started, stopped, retried or used to send
          real signals or messages from this page.
        </p>
      </aside>

      <section className="agents-grid" aria-label="Registered agents">
        {data.items.map((agent) => (
          <AgentCard agent={agent} key={agent.agent_key} />
        ))}
      </section>
    </>
  );
}
