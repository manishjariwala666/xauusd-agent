"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type {
  AdminAgent,
  AdminAgentRun,
  AdminAgentsData
} from "@/lib/agents-api";

async function getCsrfToken() {
  const response = await fetch("/api/admin/auth/csrf", {
    cache: "no-store"
  });
  return await response.json() as { csrfToken: string };
}

function readableDate(value?: string | null) {
  if (!value) return "Never";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function AgentCard({ agent }: { agent: AdminAgent }) {
  const router = useRouter();
  const [enabled, setEnabled] = useState(Boolean(agent.is_enabled));
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function toggleAgent() {
    const previous = enabled;
    const next = !previous;

    setEnabled(next);
    setBusy(true);
    setMessage("");

    try {
      const { csrfToken } = await getCsrfToken();
      const action = next ? "enable" : "disable";

      const response = await fetch(
        `/api/admin/agents/${encodeURIComponent(agent.agent_key)}/${action}`,
        {
          method: "POST",
          headers: { "X-CSRF-Token": csrfToken }
        }
      );

      const result = await response.json() as {
        detail?: string;
        message?: string;
      };

      if (!response.ok) {
        setEnabled(previous);
        setMessage(result.detail || result.message || "Agent update failed.");
        return;
      }

      setMessage(`Agent ${next ? "enabled" : "disabled"} successfully.`);
      router.refresh();
    } catch {
      setEnabled(previous);
      setMessage("Agents service is temporarily unavailable.");
    } finally {
      setBusy(false);
    }
  }

  const status = String(agent.status || "IDLE").toUpperCase();

  return (
    <article className="kpi-card">
      <small>{agent.agent_key}</small>
      <strong>{agent.display_name}</strong>
      <span>Status: {status}</span>
      <p>Last run: {readableDate(agent.last_run_at)}</p>
      <p>Success: {agent.success_count || 0} · Failure: {agent.failure_count || 0}</p>
      <p>Queue: {agent.queue_size || 0}</p>

      {agent.last_error && (
        <p role="alert"><strong>Last error:</strong> {agent.last_error}</p>
      )}

      <button
        type="button"
        disabled={busy}
        onClick={toggleAgent}
      >
        {busy ? "Updating…" : enabled ? "Turn OFF" : "Turn ON"}
      </button>

      <p><strong>Control:</strong> {enabled ? "ON" : "OFF"}</p>

      {message && <small role="status">{message}</small>}
    </article>
  );
}

function RecentRuns({ runs }: { runs: AdminAgentRun[] }) {
  if (!runs.length) {
    return (
      <section className="state-panel">
        <strong>No recent agent runs</strong>
        <p>Agent execution history is currently empty.</p>
      </section>
    );
  }

  return (
    <section>
      <div className="page-heading">
        <small>EXECUTION HISTORY</small>
        <h2>Recent runs</h2>
      </div>

      <div className="kpi-grid">
        {runs.map((run, index) => (
          <article className="kpi-card" key={run.id || run.run_id || index}>
            <small>Run #{run.id || run.run_id || "—"}</small>
            <strong>{run.display_name || run.agent_key || "Agent run"}</strong>
            <span>{run.status || "UNKNOWN"}</span>
            <p>Started: {readableDate(run.started_at)}</p>
            <p>Completed: {readableDate(run.finished_at)}</p>
            {run.error_message && <p role="alert">{run.error_message}</p>}
          </article>
        ))}
      </div>
    </section>
  );
}

export function AgentsDashboard({ data }: { data: AdminAgentsData }) {
  return (
    <>
      <section className="page-heading">
        <small>AUTOMATION CONTROL</small>
        <h1>AI Agents</h1>
        <p>View real agent status, recent runs and safely enable or disable each agent.</p>
      </section>

      {data.agents.length ? (
        <section className="kpi-grid" aria-label="AI agents">
          {data.agents.map(agent => (
            <AgentCard agent={agent} key={agent.agent_key} />
          ))}
        </section>
      ) : (
        <section className="state-panel">
          <strong>No agents found</strong>
          <p>No real agent records were returned by the backend.</p>
        </section>
      )}

      <RecentRuns runs={data.runs} />
    </>
  );
}
