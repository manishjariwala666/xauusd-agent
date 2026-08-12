"use client";

import { useMemo, useState } from "react";

import type {
  AgentDashboardRecord,
  AgentsDashboardPayload,
} from "@/lib/agents-api";

type ApprovalItem = {
  id: string;
  agentKey: string;
  agentName: string;
  officialName: string;
  action: string;
  risk: AgentDashboardRecord["default_risk"];
  status: "PENDING";
};

function humanize(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, letter => letter.toUpperCase());
}

function riskClass(
  risk: AgentDashboardRecord["default_risk"],
): string {
  return `agent-risk agent-risk-${risk
    .toLowerCase()
    .replaceAll("_", "-")}`;
}

export function AgentApprovalCenter({
  data,
}: {
  data: AgentsDashboardPayload;
}) {
  const [search, setSearch] = useState("");
  const [risk, setRisk] = useState("ALL");
  const [agentKey, setAgentKey] = useState("ALL");

  const approvals = useMemo<ApprovalItem[]>(
    () =>
      data.items.flatMap(agent =>
        agent.approval_required_actions.map(
          (action, index) => ({
            id: `${agent.agent_key}:${index}:${action}`,
            agentKey: agent.agent_key,
            agentName: agent.short_name,
            officialName: agent.official_name,
            action,
            risk: agent.default_risk,
            status: "PENDING",
          }),
        ),
      ),
    [data.items],
  );

  const filteredApprovals = useMemo(() => {
    const query = search.trim().toLowerCase();

    return approvals.filter(item => {
      const searchable = [
        item.agentKey,
        item.agentName,
        item.officialName,
        item.action,
      ]
        .join(" ")
        .toLowerCase();

      if (query && !searchable.includes(query)) {
        return false;
      }

      if (risk !== "ALL" && item.risk !== risk) {
        return false;
      }

      if (
        agentKey !== "ALL" &&
        item.agentKey !== agentKey
      ) {
        return false;
      }

      return true;
    });
  }, [agentKey, approvals, risk, search]);

  const highRiskCount = approvals.filter(
    item =>
      item.risk === "HIGH" ||
      item.risk === "CRITICAL",
  ).length;

  function clearFilters() {
    setSearch("");
    setRisk("ALL");
    setAgentKey("ALL");
  }

  return (
    <main className="studio-v2-approval-page">
      <section className="page-heading">
        <small className="eyebrow">
          AGENT GOVERNANCE
        </small>
        <h1>Global Approval Center</h1>
        <p>
          Review approval-gated actions across the complete
          VenusRealm agent registry. This phase is read-only.
        </p>
      </section>

      <section
        className="kpi-grid approval-kpi-grid"
        aria-label="Approval summary"
      >
        <article className="kpi-card">
          <small>Registered agents</small>
          <strong>{data.count}</strong>
          <span>Dynamic registry</span>
        </article>

        <article className="kpi-card">
          <small>Approval actions</small>
          <strong>{approvals.length}</strong>
          <span>Policy-gated actions</span>
        </article>

        <article className="kpi-card">
          <small>High-risk actions</small>
          <strong>{highRiskCount}</strong>
          <span>Individual review required</span>
        </article>

        <article className="kpi-card">
          <small>Execution mode</small>
          <strong>OFF</strong>
          <span>Read-only foundation</span>
        </article>
      </section>

      <aside
        className="approval-readonly-notice"
        role="status"
      >
        <strong>Approval execution disabled</strong>
        <p>
          Approve, reject, run, publish, schedule and message
          actions are not available in this phase.
        </p>
      </aside>

      <section
        className="approval-toolbar"
        aria-label="Approval filters"
      >
        <label className="approval-search-field">
          <span>Search</span>
          <input
            type="search"
            value={search}
            placeholder="Search agent or action"
            onChange={event =>
              setSearch(event.target.value)
            }
          />
        </label>

        <label>
          <span>Risk</span>
          <select
            value={risk}
            onChange={event =>
              setRisk(event.target.value)
            }
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
          <span>Agent</span>
          <select
            value={agentKey}
            onChange={event =>
              setAgentKey(event.target.value)
            }
          >
            <option value="ALL">All agents</option>
            {data.items.map(agent => (
              <option
                value={agent.agent_key}
                key={agent.agent_key}
              >
                {agent.short_name}
              </option>
            ))}
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

      <div className="approval-result-count">
        <strong>
          {filteredApprovals.length} of{" "}
          {approvals.length} approval actions
        </strong>
        <span>Registry-derived policies</span>
      </div>

      {filteredApprovals.length ? (
        <section
          className="approval-grid"
          aria-label="Approval actions"
        >
          {filteredApprovals.map(item => (
            <article
              className="approval-card"
              key={item.id}
            >
              <header>
                <div>
                  <small>{item.agentKey}</small>
                  <h2>{item.agentName}</h2>
                  <p>{item.officialName}</p>
                </div>

                <span className={riskClass(item.risk)}>
                  {humanize(item.risk)}
                </span>
              </header>

              <section>
                <span>Requested action</span>
                <strong>
                  {humanize(item.action)}
                </strong>
              </section>

              <dl>
                <div>
                  <dt>Status</dt>
                  <dd>Pending policy approval</dd>
                </div>
                <div>
                  <dt>Execution</dt>
                  <dd>Disabled</dd>
                </div>
              </dl>

              <footer>
                <span>Read-only review</span>
                <div>
                  <button type="button" disabled>
                    Reject
                  </button>
                  <button type="button" disabled>
                    Approve
                  </button>
                </div>
              </footer>
            </article>
          ))}
        </section>
      ) : (
        <section className="agent-empty-results">
          <strong>No approval actions found</strong>
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
    </main>
  );
}
