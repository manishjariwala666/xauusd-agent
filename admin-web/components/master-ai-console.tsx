"use client";

import { FormEvent, useState } from "react";

type ChatTurn = {
  role: "user" | "assistant";
  text: string;
};

const QUICK_PROMPTS = [
  "List all registered agents",
  "Explain Automatic and Owner Approval actions",
  "Show the safest next development task",
  "Explain current VenusRealm agent architecture",
];

export function MasterAIConsole() {
  const [message, setMessage] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function sendMessage(
    event?: FormEvent,
    selectedMessage?: string,
  ) {
    event?.preventDefault();

    const cleanMessage =
      (selectedMessage ?? message).trim();

    if (!cleanMessage || busy) return;

    setBusy(true);
    setError("");
    setTurns(current => [
      ...current,
      { role: "user", text: cleanMessage },
    ]);
    setMessage("");

    try {
      const csrfResponse = await fetch(
        "/api/admin/auth/csrf",
        { cache: "no-store" },
      );

      if (!csrfResponse.ok) {
        throw new Error("CSRF token could not be loaded.");
      }

      const csrfData = await csrfResponse.json() as {
        csrfToken: string;
      };

      const response = await fetch(
        "/api/admin/master-ai/chat",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrfData.csrfToken,
          },
          body: JSON.stringify({
            message: cleanMessage,
          }),
        },
      );

      const result = await response.json() as {
        reply?: string;
        message?: string;
      };

      if (!response.ok || !result.reply) {
        throw new Error(
          result.message ||
          "Master AI response could not be loaded.",
        );
      }

      setTurns(current => [
        ...current,
        {
          role: "assistant",
          text: result.reply || "",
        },
      ]);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Master AI is temporarily unavailable.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="master-ai-console-page">
      <section className="page-heading">
        <small className="eyebrow">
          EXECUTIVE INTELLIGENCE
        </small>
        <h1>Master AI Console</h1>
        <p>
          Talk with VenusRealm Master AI inside the secured
          admin workspace.
        </p>
      </section>

      <aside className="master-ai-safety-banner">
        <strong>Conversation-only foundation</strong>
        <p>
          Agent execution, messaging, signals, publishing,
          deployment and infrastructure changes remain locked.
        </p>
      </aside>

      <section className="master-ai-layout">
        <div className="master-ai-chat-panel">
          <div className="master-ai-chat-history">
            {turns.length === 0 ? (
              <div className="master-ai-empty">
                <strong>Master AI is ready</strong>
                <p>
                  Ask about agents, policies, architecture,
                  status interpretation or safe planning.
                </p>
              </div>
            ) : (
              turns.map((turn, index) => (
                <article
                  className={`master-ai-turn master-ai-turn-${turn.role}`}
                  key={`${turn.role}-${index}`}
                >
                  <small>
                    {turn.role === "user"
                      ? "YOU"
                      : "MASTER AI"}
                  </small>
                  <p>{turn.text}</p>
                </article>
              ))
            )}
          </div>

          {error ? (
            <div className="form-error" role="alert">
              {error}
            </div>
          ) : null}

          <form
            className="master-ai-composer"
            onSubmit={event => void sendMessage(event)}
          >
            <textarea
              value={message}
              maxLength={4_000}
              placeholder="Ask Master AI…"
              onChange={event =>
                setMessage(event.target.value)
              }
            />

            <button
              type="submit"
              className="primary-button"
              disabled={busy || !message.trim()}
            >
              {busy ? "Thinking…" : "Send"}
            </button>
          </form>
        </div>

        <aside className="master-ai-side-panel">
          <section>
            <h2>Quick prompts</h2>

            {QUICK_PROMPTS.map(prompt => (
              <button
                type="button"
                key={prompt}
                disabled={busy}
                onClick={() =>
                  void sendMessage(undefined, prompt)
                }
              >
                {prompt}
              </button>
            ))}
          </section>

          <section>
            <h2>Safety levels</h2>
            <p><strong>Automatic:</strong> safe read, analysis and drafts.</p>
            <p><strong>Owner approval:</strong> external-impact actions.</p>
            <p><strong>Forbidden:</strong> permanently blocked actions.</p>
          </section>
        </aside>
      </section>
    </main>
  );
}
