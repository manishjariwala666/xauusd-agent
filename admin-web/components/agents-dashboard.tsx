"use client";

import { useMemo, useState } from "react";

import type {
  AgentDashboardRecord,
  AgentsDashboardPayload,
} from "@/lib/agents-api";

function humanize(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, letter => letter.toUpperCase());
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
          {items.map(item => (
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
  busy,
  onToggle,
}: {
  agent: AgentDashboardRecord;
  busy: boolean;
  onToggle: (agent: AgentDashboardRecord) => void;
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
          <span className="agent-brain agent-brain-ready">
            {humanize(agent.capability_mode)}
          </span>
        </div>
      </header>

      <p className="agent-purpose">{agent.purpose}</p>

      <dl className="agent-summary">
        <div>
          <dt>Status</dt>
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
          <dt>Last run</dt>
          <dd>{agent.last_run_at || "Never"}</dd>
        </div>
        <div>
          <dt>Last error</dt>
          <dd>{agent.last_error || "None"}</dd>
        </div>
        <div>
          <dt>Success / failure</dt>
          <dd>{agent.success_count} / {agent.failure_count}</dd>
        </div>
        <div>
          <dt>Queue</dt>
          <dd>{agent.queue_size}</dd>
        </div>
        <div>
          <dt>Schedule</dt>
          <dd>
            {agent.next_scheduled_run_at ||
              (agent.schedule_minutes
                ? `Every ${agent.schedule_minutes} min`
                : "Not scheduled")}
          </dd>
        </div>
        <div>
          <dt>Owner approval</dt>
          <dd>{agent.owner_approval_required ? "Required" : "Not required"}</dd>
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
        <span>
          {agent.can_toggle
            ? "Guarded runtime control"
            : agent.owner_approval_required
              ? "Runtime control locked · owner approval policy"
              : "Status only · no direct toggle exposed"}
        </span>

        {agent.can_toggle ? (
          <button
            type="button"
            className={
              agent.is_enabled
                ? "agent-toggle-button agent-toggle-disable"
                : "agent-toggle-button agent-toggle-enable"
            }
            disabled={
              busy ||
              agent.is_enabled === null ||
              !agent.is_configured
            }
            onClick={() => onToggle(agent)}
          >
            {busy
              ? "Updating…"
              : agent.is_enabled
                ? "Turn OFF"
                : "Turn ON"}
          </button>
        ) : null}
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
  const [agentItems, setAgentItems] =
    useState<AgentDashboardRecord[]>(data.items);
  const [toggleBusy, setToggleBusy] = useState<string | null>(null);
  const [controlMessage, setControlMessage] = useState("");

  const configured = agentItems.filter(agent => agent.brain_configured).length;
  const enabled = agentItems.filter(agent => agent.is_enabled === true).length;
  const errors = agentItems.filter(
    agent => agent.status === "ERROR" || Boolean(agent.last_error),
  ).length;
  const approvalGated = agentItems.filter(
    agent => agent.owner_approval_required,
  ).length;

  const statuses = useMemo(
    () => Array.from(new Set(agentItems.map(agent => agent.status))).sort(),
    [agentItems],
  );

  const filteredAgents = useMemo(() => {
    const query = search.trim().toLowerCase();
    return agentItems.filter(agent => {
      const searchable = [
        agent.agent_key,
        agent.short_name,
        agent.official_name,
        agent.purpose,
        ...agent.aliases,
      ]
        .join(" ")
        .toLowerCase();

      return (
        (!query || searchable.includes(query)) &&
        (risk === "ALL" || agent.default_risk === risk) &&
        (status === "ALL" || agent.status === status)
      );
    });
  }, [agentItems, risk, search, status]);

  async function toggleBlogAgent(agent: AgentDashboardRecord) {
    if (
      !agent.can_toggle ||
      agent.is_enabled === null ||
      toggleBusy
    ) {
      return;
    }

    const nextEnabled = !agent.is_enabled;
    const confirmed = window.confirm(
      nextEnabled
        ? "Turn AI Blog Agent ON?"
        : "Turn AI Blog Agent OFF?",
    );
    if (!confirmed) return;

    setToggleBusy(agent.agent_key);
    setControlMessage("Updating AI Blog Agent…");

    try {
      const csrfResponse = await fetch(
        "/api/admin/auth/csrf",
        { cache: "no-store" },
      );
      if (!csrfResponse.ok) {
        throw new Error("CSRF token could not be loaded.");
      }
      const csrfData = await csrfResponse.json() as { csrfToken: string };

      const response = await fetch(
        `/api/admin/agents/${agent.agent_key}/enabled`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrfData.csrfToken,
          },
          body: JSON.stringify({ enabled: nextEnabled }),
        },
      );
      const result = await response.json() as {
        enabled?: boolean;
        message?: string;
        detail?: string;
      };
      if (!response.ok || typeof result.enabled !== "boolean") {
        throw new Error(
          result.detail || result.message || "Agent state could not be updated.",
        );
      }

      setAgentItems(current =>
        current.map(item =>
          item.agent_key === agent.agent_key
            ? { ...item, is_enabled: result.enabled ?? item.is_enabled }
            : item,
        ),
      );
      setControlMessage(result.message || "AI Blog Agent state updated.");
    } catch (caught) {
      setControlMessage(
        caught instanceof Error
          ? caught.message
          : "Agent control service is temporarily unavailable.",
      );
    } finally {
      setToggleBusy(null);
    }
  }

  return (
    <>
      <section className="page-heading agents-heading">
        <small className="eyebrow">AGENT OPERATIONS</small>
        <h1>VenusRealm Agents</h1>
        <p>
          Verified registry, runtime state and policy boundaries. Only the
          existing guarded AI Blog Agent toggle is exposed; locked agents do
          not receive cosmetic or simulated controls.
        </p>
      </section>

      <section className="kpi-grid agent-kpi-grid" aria-label="Agent summary">
        <article className="kpi-card">
          <small>Registered</small>
          <strong>{data.count}</strong>
          <span>{configured} brains configured</span>
        </article>
        <article className="kpi-card">
          <small>Enabled</small>
          <strong>{enabled}</strong>
          <span>Current runtime truth</span>
        </article>
        <article className="kpi-card">
          <small>Errors</small>
          <strong>{errors}</strong>
          <span>Safe runtime error state</span>
        </article>
        <article className="kpi-card">
          <small>Approval gated</small>
          <strong>{approvalGated}</strong>
          <span>Owner approval required</span>
        </article>
      </section>

      <aside className="agents-readonly-notice" role="status">
        <strong>Truthful control mode</strong>
        <p>
          Signal, reply, announcement, SEO, publishing and other consequential
          agents remain policy locked. No local-only preview toggle is presented
          as a runtime control.
        </p>
        {controlMessage ? <p className="agent-control-message">{controlMessage}</p> : null}
      </aside>

      <section className="agent-registry-toolbar" aria-label="Agent filters">
        <label className="agent-search-field">
          <span>Search</span>
          <input
            type="search"
            value={search}
            placeholder="Agent name, key or purpose"
            onChange={event => setSearch(event.target.value)}
          />
        </label>
        <label>
          <span>Risk</span>
          <select value={risk} onChange={event => setRisk(event.target.value)}>
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
          <select value={status} onChange={event => setStatus(event.target.value)}>
            <option value="ALL">All statuses</option>
            {statuses.map(item => (
              <option value={item} key={item}>{humanize(item)}</option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="secondary-button"
          onClick={() => {
            setSearch("");
            setRisk("ALL");
            setStatus("ALL");
          }}
        >
          Clear
        </button>
      </section>

      <div className="agent-registry-results">
        <strong>{filteredAgents.length} of {data.count} agents</strong>
        <span>Verified backend records</span>
      </div>

      <section className="agents-grid" aria-label="Registered agents">
        {filteredAgents.map(agent => (
          <AgentCard
            key={agent.agent_key}
            agent={agent}
            busy={toggleBusy === agent.agent_key}
            onToggle={toggleBlogAgent}
          />
        ))}
      </section>
    </>
  );
}
