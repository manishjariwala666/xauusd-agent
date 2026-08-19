"use client";

import { useEffect, useState } from "react";

type CaptainStatus = {
  mode?: string;
  decision?: string;
  direction?: string;
  confidence?: number;
  live_cmp?: string | null;
  buy_base?: string | null;
  sell_base?: string | null;
  stop_loss?: string | null;
  news_locked?: boolean;
  macro_bias?: string;
  macro_confidence?: number;
  reasons?: string[];
  observed_market?: {
    signal_date?: string;
    day_high?: string | null;
    day_low?: string | null;
    buy_base?: string | null;
    sell_base?: string | null;
    next_buy_target?: string | null;
    next_sell_target?: string | null;
    verification?: string;
  };
};

function value(input: unknown) {
  return input === null || input === undefined || input === ""
    ? "—"
    : String(input);
}

export function CaptainStatusPanel() {
  const [status, setStatus] = useState<CaptainStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetch(
          "/api/admin/master-ai/status",
          { cache: "no-store" },
        );
        const data = await response.json() as CaptainStatus & {
          message?: string;
        };
        if (!response.ok) {
          throw new Error(
            data.message || "Captain status could not be loaded.",
          );
        }
        if (!cancelled) {
          setStatus(data);
          setError("");
        }
      } catch (caught) {
        if (!cancelled) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Captain status is temporarily unavailable.",
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

  return (
    <section className="master-ai-safety-banner">
      <strong>Live read-only Captain / Sheet status</strong>
      {error ? (
        <p>{error}</p>
      ) : status ? (
        <div>
          <p>
            <strong>Decision:</strong> {value(status.decision)} ·{" "}
            <strong>Direction:</strong> {value(status.direction)} ·{" "}
            <strong>Confidence:</strong> {value(status.confidence)}%
          </p>
          <p>
            <strong>CMP:</strong> {value(status.live_cmp)} ·{" "}
            <strong>Buy Base:</strong> {value(status.buy_base)} ·{" "}
            <strong>Sell Base:</strong> {value(status.sell_base)} ·{" "}
            <strong>SL:</strong> {value(status.stop_loss)}
          </p>
          <p>
            <strong>Session:</strong>{" "}
            {value(status.observed_market?.signal_date)} ·{" "}
            <strong>High:</strong>{" "}
            {value(status.observed_market?.day_high)} ·{" "}
            <strong>Low:</strong>{" "}
            {value(status.observed_market?.day_low)}
          </p>
          <p>
            <strong>Next BUY target:</strong>{" "}
            {value(status.observed_market?.next_buy_target)} ·{" "}
            <strong>Next SELL target:</strong>{" "}
            {value(status.observed_market?.next_sell_target)}
          </p>
          <p>
            <strong>News lock:</strong>{" "}
            {status.news_locked ? "LOCKED" : "CLEAR"} ·{" "}
            <strong>Macro:</strong> {value(status.macro_bias)} ({value(status.macro_confidence)}%)
          </p>
          {status.reasons?.length ? (
            <p><strong>Reason:</strong> {status.reasons[0]}</p>
          ) : null}
        </div>
      ) : (
        <p>Loading verified Captain and Google Sheet state…</p>
      )}
    </section>
  );
}
