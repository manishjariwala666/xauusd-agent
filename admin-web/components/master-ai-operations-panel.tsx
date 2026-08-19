"use client";

import { useEffect, useState } from "react";

type OperationsStatus = {
  read_only: boolean;
  master_ai: {
    shared_backend: string;
    interfaces: string[];
    execution_mode: string;
    agents: {
      available: boolean;
      count: number;
      enabled: number;
      errors: number;
    };
    runs: {
      available: boolean;
      reason?: string;
      items: Array<{
        run_id?: number;
        title?: string;
        task_type?: string;
        status?: string;
        completed_steps?: number;
        total_steps?: number;
        failed_steps?: number;
        safe_error?: string | null;
      }>;
    };
  };
  signal: {
    available: boolean;
    reason?: string;
    correlation_id?: string;
    recorded_at?: string;
    signal_date?: string;
    cmp?: string | null;
    high?: string | null;
    low?: string | null;
    buy_base?: string | null;
    sell_base?: string | null;
    captain_decision?: string;
    captain_direction?: string;
    captain_confidence?: number;
    shadow_status?: string;
    shadow_reason?: string | null;
    telegram_delivered?: boolean | null;
    whatsapp_delivered?: boolean | null;
  };
  content: {
    available: boolean;
    reason?: string;
    drafts?: number;
    published?: number;
    automatic_publish?: boolean;
    items: Array<{
      id?: number;
      title?: string;
      status?: string;
      featured_image?: string | null;
      word_count?: number;
    }>;
  };
  delivery: {
    available: boolean;
    reason?: string;
    max_attempts: number;
    stale_claim_minutes: number;
    channels: Record<
      string,
      { sent: number; pending: number; failed: number }
    >;
    failed_recipients: Array<{
      signal_id?: number;
      channel?: string;
      recipient?: string;
      attempts?: number;
      error_category?: string;
    }>;
    duplicate_prevention?: string;
  };
  safety: Record<string, string | boolean>;
};

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "YES" : "NO";
  return String(value);
}

function deliveryState(value: boolean | null | undefined): string {
  if (value === true) return "DELIVERED";
  if (value === false) return "NOT DELIVERED";
  return "UNKNOWN";
}

export function MasterAIOperationsPanel() {
  const [data, setData] = useState<OperationsStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetch(
          "/api/admin/master-ai/operations",
          { cache: "no-store" },
        );
        const payload = await response.json() as OperationsStatus & {
          message?: string;
        };
        if (!response.ok) {
          throw new Error(
            payload.message ||
            "Operations status could not be loaded.",
          );
        }
        if (!cancelled) {
          setData(payload);
          setError("");
        }
      } catch (caught) {
        if (!cancelled) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Operations status is temporarily unavailable.",
          );
        }
      }
    }

    void load();
    const timer = window.setInterval(() => void load(), 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  if (error) {
    return (
      <section className="state-panel error-state">
        <strong>Operations status unavailable</strong>
        <p>{error}</p>
        <p>No execution or external delivery was attempted.</p>
      </section>
    );
  }

  if (!data) {
    return (
      <section className="state-panel">
        <strong>Loading verified operations status…</strong>
      </section>
    );
  }

  const telegram = data.delivery.channels.telegram;
  const whatsapp = data.delivery.channels.whatsapp;

  return (
    <section className="agent-dashboard-shell">
      <header className="page-heading">
        <small className="eyebrow">OWNER OPERATIONS</small>
        <h2>Launch Readiness & Runtime Truth</h2>
        <p>
          Read-only status from the shared Master AI, canonical Captain audit,
          CMS records and durable delivery ledger.
        </p>
      </header>

      <div className="agent-action-grid">
        <section className="agent-action-group">
          <h3>Master AI</h3>
          <p><strong>Backend:</strong> {display(data.master_ai.shared_backend)}</p>
          <p><strong>Interfaces:</strong> {data.master_ai.interfaces.join(" + ")}</p>
          <p><strong>Execution:</strong> {display(data.master_ai.execution_mode)}</p>
          <p>
            <strong>Agents:</strong>{" "}
            {data.master_ai.agents.available
              ? `${data.master_ai.agents.enabled}/${data.master_ai.agents.count} enabled · ${data.master_ai.agents.errors} errors`
              : "runtime unavailable"}
          </p>
        </section>

        <section className="agent-action-group">
          <h3>Signal / Captain / Shadow</h3>
          {data.signal.available ? (
            <>
              <p>
                <strong>Date:</strong> {display(data.signal.signal_date)} ·{" "}
                <strong>CMP:</strong> {display(data.signal.cmp)}
              </p>
              <p>
                <strong>High / Low:</strong> {display(data.signal.high)} / {display(data.signal.low)}
              </p>
              <p>
                <strong>Buy / Sell Base:</strong> {display(data.signal.buy_base)} / {display(data.signal.sell_base)}
              </p>
              <p>
                <strong>Captain:</strong> {display(data.signal.captain_decision)} {display(data.signal.captain_direction)} · {display(data.signal.captain_confidence)}%
              </p>
              <p>
                <strong>Shadow:</strong> {display(data.signal.shadow_status)} · {display(data.signal.shadow_reason)}
              </p>
              <p><strong>Correlation:</strong> {display(data.signal.correlation_id)}</p>
              <p>
                <strong>Telegram:</strong> {deliveryState(data.signal.telegram_delivered)} ·{" "}
                <strong>WhatsApp:</strong> {deliveryState(data.signal.whatsapp_delivered)}
              </p>
            </>
          ) : (
            <p>
              Verified canonical audit unavailable: {display(data.signal.reason)}.
              No Captain/Shadow result is inferred.
            </p>
          )}
        </section>

        <section className="agent-action-group">
          <h3>Durable Delivery</h3>
          {data.delivery.available ? (
            <>
              <p>
                <strong>Telegram:</strong>{" "}
                {telegram ? `${telegram.sent} sent · ${telegram.pending} pending · ${telegram.failed} failed` : "no ledger rows"}
              </p>
              <p>
                <strong>WhatsApp:</strong>{" "}
                {whatsapp ? `${whatsapp.sent} sent · ${whatsapp.pending} pending · ${whatsapp.failed} failed` : "no ledger rows"}
              </p>
              <p>
                <strong>Retry:</strong> max {data.delivery.max_attempts} · stale claim {data.delivery.stale_claim_minutes} min
              </p>
              <p>
                <strong>Idempotency:</strong> {display(data.delivery.duplicate_prevention)}
              </p>
            </>
          ) : (
            <p>
              Durable ledger unavailable: {display(data.delivery.reason)}.
              Delivery is not shown as successful.
            </p>
          )}
        </section>

        <section className="agent-action-group">
          <h3>Content</h3>
          {data.content.available ? (
            <>
              <p>
                <strong>Recent drafts / published:</strong>{" "}
                {display(data.content.drafts)} / {display(data.content.published)}
              </p>
              <p>
                <strong>Automatic publish:</strong>{" "}
                {data.content.automatic_publish ? "ENABLED" : "LOCKED"}
              </p>
              {data.content.items.slice(0, 3).map(item => (
                <p key={item.id}>
                  #{display(item.id)} {display(item.title)} · {display(item.status)} · {display(item.word_count)} words · image {item.featured_image ? "YES" : "NO"}
                </p>
              ))}
            </>
          ) : (
            <p>Content status unavailable: {display(data.content.reason)}.</p>
          )}
        </section>
      </div>

      <div className="agent-action-grid">
        <section className="agent-action-group">
          <h3>Recent Master AI runs</h3>
          {data.master_ai.runs.available && data.master_ai.runs.items.length ? (
            data.master_ai.runs.items.slice(0, 5).map(run => (
              <p key={run.run_id}>
                #{display(run.run_id)} {display(run.title)} · {display(run.status)} · {display(run.completed_steps)}/{display(run.total_steps)} complete · {display(run.failed_steps)} failed
                {run.safe_error ? ` · ${run.safe_error}` : ""}
              </p>
            ))
          ) : (
            <p>
              No verified run rows available{data.master_ai.runs.reason ? `: ${data.master_ai.runs.reason}` : "."}
            </p>
          )}
        </section>

        <section className="agent-action-group">
          <h3>Failed recipient retries</h3>
          {data.delivery.failed_recipients.length ? (
            data.delivery.failed_recipients.slice(0, 8).map((item, index) => (
              <p key={`${item.signal_id}-${item.channel}-${item.recipient}-${index}`}>
                Signal #{display(item.signal_id)} · {display(item.channel)} · recipient {display(item.recipient)}… · attempt {display(item.attempts)}/{data.delivery.max_attempts} · {display(item.error_category)}
              </p>
            ))
          ) : (
            <p>No failed recipient row is present in the loaded ledger window.</p>
          )}
        </section>

        <section className="agent-action-group">
          <h3>Safety locks</h3>
          {Object.entries(data.safety).map(([key, value]) => (
            <p key={key}>
              <strong>{key.replaceAll("_", " ")}:</strong> {display(value)}
            </p>
          ))}
        </section>
      </div>
    </section>
  );
}
