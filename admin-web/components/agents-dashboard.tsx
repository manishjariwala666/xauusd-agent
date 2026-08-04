"use client";

import { useMemo, useState } from "react";

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

function AgentCard({
  agent,
  onOpen,
}: {
  agent: AgentDashboardRecord;
  onOpen: (agent: AgentDashboardRecord) => void;
}) {
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
          <dt>Live status</dt>
          <dd>{humanize(agent.status)}</dd>
        </div>
        <div>
          <dt>Enabled</dt>
          <dd>
            {agent.is_enabled === null
              ? "Not configured"
              : agent.is_enabled
                ? "Yes"
                : "No"}
          </dd>
        </div>
        <div>
          <dt>Queue</dt>
          <dd>{agent.queue_size}</dd>
        </div>
        <div>
          <dt>Success / failure</dt>
          <dd>
            {agent.success_count} / {agent.failure_count}
          </dd>
        </div>
        <div>
          <dt>Last run</dt>
          <dd>{agent.last_run_at || "Never"}</dd>
        </div>
        <div>
          <dt>Next scheduled run</dt>
          <dd>{agent.next_scheduled_run_at || "Not scheduled"}</dd>
        </div>
        <div>
          <dt>Last duration</dt>
          <dd>
            {agent.last_duration_ms === null
              ? "Unknown"
              : `${agent.last_duration_ms} ms`}
          </dd>
        </div>
        <div>
          <dt>Direct run</dt>
          <dd>
            {agent.run_action
              ? humanize(agent.run_action)
              : "Not registered"}
          </dd>
        </div>
      </dl>

      {agent.last_error ? (
        <section className="agent-action-group">
          <h3>Last safe error</h3>
          <p>{agent.last_error}</p>
        </section>
      ) : null}

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
        <button
          type="button"
          onClick={() => onOpen(agent)}
        >
          View details
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
  const [search, setSearch] = useState("");
  const [risk, setRisk] = useState("ALL");
  const [status, setStatus] = useState("ALL");
  const [brain, setBrain] = useState("ALL");
  const [sort, setSort] = useState("NAME_ASC");
  const [selectedAgent, setSelectedAgent] =
    useState<AgentDashboardRecord | null>(null);

  const configured = data.items.filter(
    agent => agent.brain_configured,
  ).length;

  const highRisk = data.items.filter(
    agent =>
      agent.default_risk === "HIGH" ||
      agent.default_risk === "CRITICAL",
  ).length;

  const approvalGated = data.items.filter(
    agent => agent.approval_required_actions.length > 0,
  ).length;

  const statuses = useMemo(
    () =>
      Array.from(
        new Set(data.items.map(agent => agent.status)),
      ).sort(),
    [data.items],
  );

  const filteredAgents = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();

    const riskOrder: Record<string, number> = {
      CRITICAL: 5,
      HIGH: 4,
      LOW: 3,
      READ_ONLY: 2,
      UNKNOWN: 1,
    };

    return data.items
      .filter(agent => {
        const searchable = [
          agent.agent_key,
          agent.short_name,
          agent.official_name,
          agent.purpose,
          agent.description,
          ...agent.aliases,
        ]
          .join(" ")
          .toLowerCase();

        if (
          normalizedSearch &&
          !searchable.includes(normalizedSearch)
        ) {
          return false;
        }

        if (
          risk !== "ALL" &&
          agent.default_risk !== risk
        ) {
          return false;
        }

        if (
          status !== "ALL" &&
          agent.status !== status
        ) {
          return false;
        }

        if (
          brain === "READY" &&
          !agent.brain_configured
        ) {
          return false;
        }

        if (
          brain === "MISSING" &&
          agent.brain_configured
        ) {
          return false;
        }

        return true;
      })
      .sort((left, right) => {
        if (sort === "NAME_DESC") {
          return right.short_name.localeCompare(
            left.short_name,
          );
        }

        if (sort === "RISK_DESC") {
          return (
            (riskOrder[right.default_risk] || 0) -
            (riskOrder[left.default_risk] || 0)
          );
        }

        if (sort === "STATUS") {
          return left.status.localeCompare(right.status);
        }

        return left.short_name.localeCompare(
          right.short_name,
        );
      });
  }, [brain, data.items, risk, search, sort, status]);

  function clearFilters() {
    setSearch("");
    setRisk("ALL");
    setStatus("ALL");
    setBrain("ALL");
    setSort("NAME_ASC");
  }

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

      <section
        className="agent-registry-toolbar"
        aria-label="Agent registry filters"
      >
        <label className="agent-search-field">
          <span>Search agents</span>
          <input
            type="search"
            value={search}
            placeholder="Search name, key or purpose"
            onChange={event => setSearch(event.target.value)}
          />
        </label>

        <label>
          <span>Risk</span>
          <select
            value={risk}
            onChange={event => setRisk(event.target.value)}
          >
            <option value="ALL">All risks</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="LOW">Low</option>
            <option value="READ_ONLY">Read only</option>
            <option value="UNKNOWN">Unknown</option>
          </select>
        </label>

        <label>
          <span>Status</span>
          <select
            value={status}
            onChange={event => setStatus(event.target.value)}
          >
            <option value="ALL">All statuses</option>
            {statuses.map(item => (
              <option value={item} key={item}>
                {humanize(item)}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Brain</span>
          <select
            value={brain}
            onChange={event => setBrain(event.target.value)}
          >
            <option value="ALL">All brains</option>
            <option value="READY">Configured</option>
            <option value="MISSING">Missing</option>
          </select>
        </label>

        <label>
          <span>Sort</span>
          <select
            value={sort}
            onChange={event => setSort(event.target.value)}
          >
            <option value="NAME_ASC">Name A–Z</option>
            <option value="NAME_DESC">Name Z–A</option>
            <option value="RISK_DESC">Highest risk</option>
            <option value="STATUS">Status</option>
          </select>
        </label>

        <button
          type="button"
          className="secondary-button"
          onClick={clearFilters}
        >
          Clear
        </button>
      </section>

      <div className="agent-registry-results">
        <strong>
          {filteredAgents.length} of {data.count} agents
        </strong>
        <span>Read-only registry results</span>
      </div>

      {filteredAgents.length > 0 ? (
        <section
          className="agents-grid"
          aria-label="Registered agents"
        >
          {filteredAgents.map(agent => (
            <AgentCard
              agent={agent}
              key={agent.agent_key}
              onOpen={setSelectedAgent}
            />
          ))}
        </section>
      ) : (
        <section className="agent-empty-results">
          <strong>No matching agents</strong>
          <p>
            Search ya filters change karke dobara dekhein.
          </p>
          <button
            type="button"
            className="secondary-button"
            onClick={clearFilters}
          >
            Clear filters
          </button>
        </section>
      )}

      {selectedAgent ? (
        <div
          className="agent-detail-overlay"
          role="presentation"
          onMouseDown={event => {
            if (event.target === event.currentTarget) {
              setSelectedAgent(null);
            }
          }}
        >
          <aside
            className="agent-detail-drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="agent-detail-title"
          >
            <header className="agent-detail-header">
              <div>
                <small>{selectedAgent.agent_key}</small>
                <h2 id="agent-detail-title">
                  {selectedAgent.short_name}
                </h2>
                <p>{selectedAgent.official_name}</p>
              </div>

              <button
                type="button"
                aria-label="Close agent details"
                onClick={() => setSelectedAgent(null)}
              >
                ×
              </button>
            </header>

            <div className="agent-detail-badges">
              <span className={riskClass(selectedAgent.default_risk)}>
                {humanize(selectedAgent.default_risk)}
              </span>

              <span
                className={
                  selectedAgent.brain_configured
                    ? "agent-brain agent-brain-ready"
                    : "agent-brain agent-brain-missing"
                }
              >
                {selectedAgent.brain_configured
                  ? "Brain ready"
                  : "Brain missing"}
              </span>
            </div>

            <section className="agent-detail-section">
              <h3>Purpose</h3>
              <p>{selectedAgent.purpose}</p>
              <p>{selectedAgent.description}</p>
            </section>

            <dl className="agent-detail-summary">
              <div>
                <dt>Status</dt>
                <dd>{humanize(selectedAgent.status)}</dd>
              </div>
              <div>
                <dt>Enabled</dt>
                <dd>
                  {selectedAgent.is_enabled === null
                    ? "Not configured"
                    : selectedAgent.is_enabled
                      ? "Yes"
                      : "No"}
                </dd>
              </div>
              <div>
                <dt>Queue</dt>
                <dd>{selectedAgent.queue_size}</dd>
              </div>
              <div>
                <dt>Success / failure</dt>
                <dd>
                  {selectedAgent.success_count}
                  {" / "}
                  {selectedAgent.failure_count}
                </dd>
              </div>
              <div>
                <dt>Last run</dt>
                <dd>{selectedAgent.last_run_at || "Never"}</dd>
              </div>
              <div>
                <dt>Next run</dt>
                <dd>
                  {selectedAgent.next_scheduled_run_at ||
                    "Not scheduled"}
                </dd>
              </div>
              <div>
                <dt>Direct run</dt>
                <dd>
                  {selectedAgent.run_action
                    ? humanize(selectedAgent.run_action)
                    : "Not registered"}
                </dd>
              </div>
              <div>
                <dt>Last duration</dt>
                <dd>
                  {selectedAgent.last_duration_ms === null
                    ? "Unknown"
                    : `${selectedAgent.last_duration_ms} ms`}
                </dd>
              </div>
            </dl>

            {selectedAgent.aliases.length > 0 ? (
              <section className="agent-detail-section">
                <h3>Aliases</h3>
                <div className="agent-detail-tags">
                  {selectedAgent.aliases.map(alias => (
                    <span key={alias}>{alias}</span>
                  ))}
                </div>
              </section>
            ) : null}

            <ActionList
              title="Automatic actions"
              items={selectedAgent.automatic_actions}
              emptyLabel="No automatic actions."
            />

            <ActionList
              title="Approval required"
              items={selectedAgent.approval_required_actions}
              emptyLabel="No approval-gated actions."
            />

            <ActionList
              title="Forbidden actions"
              items={selectedAgent.forbidden_actions}
              emptyLabel="No forbidden actions listed."
            />

            <ActionList
              title="Output schema"
              items={selectedAgent.output_schema}
              emptyLabel="No output schema configured."
            />

            {selectedAgent.last_error ? (
              <section className="agent-detail-section agent-detail-error">
                <h3>Last safe error</h3>
                <p>{selectedAgent.last_error}</p>
              </section>
            ) : null}

            <footer className="agent-detail-footer">
              <strong>Read-only safety mode</strong>
              <span>
                No agent action can be executed from this drawer.
              </span>
            </footer>
          </aside>
        </div>
      ) : null}
    </>
  );
}
