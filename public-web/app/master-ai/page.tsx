"use client";


import { FormEvent, useEffect, useState } from "react";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export default function MasterAIPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: "Namaste. Main VenusRealm Master AI hoon. Aap kya poochna chahte hain?",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [memoryLoaded, setMemoryLoaded] = useState(false);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem("venusrealm-master-ai-chat");

      if (saved) {
        const parsed = JSON.parse(saved) as ChatMessage[];

        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed);
        }
      }
    } catch {
      window.localStorage.removeItem("venusrealm-master-ai-chat");
    } finally {
      setMemoryLoaded(true);
    }
  }, []);

  useEffect(() => {
    if (!memoryLoaded) {
      return;
    }

    window.localStorage.setItem(
      "venusrealm-master-ai-chat",
      JSON.stringify(messages)
    );
  }, [messages, memoryLoaded]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const message = input.trim();

    if (!message || isLoading) {
      return;
    }

    setMessages((current) => [
      ...current,
      { role: "user", content: message },
    ]);
    setInput("");
    setError("");
    setIsLoading(true);

    try {
      const response = await fetch("/api/master-ai", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      });

      const data = (await response.json()) as {
        answer?: string;
        error?: string;
      };

      if (!response.ok || !data.answer) {
        throw new Error(data.error || "Master AI response failed.");
      }

      setMessages((current) => [
        ...current,
        { role: "assistant", content: data.answer as string },
      ]);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Master AI request failed."
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "48px 20px" }}>
      <header style={{ marginBottom: 28 }}>
        <p style={{ margin: 0, opacity: 0.7 }}>VenusRealm</p>
        <h1 style={{ margin: "8px 0" }}>Master AI</h1>
        <p style={{ margin: 0, opacity: 0.75 }}>
          Private AI assistant prototype. Trading execution and publishing are disabled.
        </p>
      </header>

      <section
        aria-live="polite"
        style={{
          minHeight: 420,
          border: "1px solid rgba(128,128,128,0.3)",
          borderRadius: 16,
          padding: 20,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            style={{
              alignSelf:
                message.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "80%",
              padding: "12px 16px",
              borderRadius: 14,
              background:
                message.role === "user"
                  ? "rgba(70,110,255,0.18)"
                  : "rgba(128,128,128,0.14)",
              whiteSpace: "pre-wrap",
            }}
          >
            {message.content}
          </div>
        ))}

        {isLoading && (
          <div style={{ opacity: 0.7 }}>Master AI soch raha hai...</div>
        )}
      </section>

      <form
        onSubmit={handleSubmit}
        style={{ display: "flex", gap: 12, marginTop: 18 }}
      >
        <label htmlFor="master-ai-message" style={{ position: "absolute", left: -9999 }}>
          Message
        </label>

        <input
          id="master-ai-message"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Master AI se baat karein..."
          maxLength={4000}
          disabled={isLoading}
          style={{
            flex: 1,
            minHeight: 48,
            padding: "0 16px",
            borderRadius: 12,
            border: "1px solid rgba(128,128,128,0.4)",
            background: "transparent",
            color: "inherit",
          }}
        />

        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          style={{
            minWidth: 110,
            border: 0,
            borderRadius: 12,
            padding: "0 20px",
            cursor: "pointer",
          }}
        >
          {isLoading ? "Sending..." : "Send"}
        </button>
      </form>

      {error && (
        <p role="alert" style={{ marginTop: 12 }}>
          {error}
        </p>
      )}
    </main>
  );
}
