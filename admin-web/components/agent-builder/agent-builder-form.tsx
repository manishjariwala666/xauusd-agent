"use client";

import { FormEvent, useState } from "react";

export type AgentBuilderSpec = {
  display_name: string;
  agent_key?: string;
  department: string;
  purpose: string;
  risk?: string;
  read_only: boolean;
  requested_actions: string[];
  requested_tools: string[];
  allowed_inputs: string[];
  output_schema: string[];
};

function splitList(value: string): string[] {
  return value
    .split(",")
    .map(item => item.trim())
    .filter(Boolean);
}

export function AgentBuilderForm({
  busy,
  onSubmit,
}: {
  busy: boolean;
  onSubmit: (spec: AgentBuilderSpec) => void;
}) {
  const [displayName, setDisplayName] = useState("");
  const [agentKey, setAgentKey] = useState("");
  const [department, setDepartment] = useState("general");
  const [purpose, setPurpose] = useState("");
  const [risk, setRisk] = useState("");
  const [readOnly, setReadOnly] = useState(false);
  const [actions, setActions] = useState("");
  const [tools, setTools] = useState("");
  const [inputs, setInputs] = useState("");
  const [outputs, setOutputs] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    onSubmit({
      display_name: displayName.trim(),
      agent_key: agentKey.trim() || undefined,
      department,
      purpose: purpose.trim(),
      risk: risk || undefined,
      read_only: readOnly,
      requested_actions: splitList(actions),
      requested_tools: splitList(tools),
      allowed_inputs: splitList(inputs),
      output_schema: splitList(outputs),
    });
  }

  return (
    <form className="agent-builder-form" onSubmit={submit}>
      <div className="agent-builder-field-grid">
        <label>
          <span>Agent name</span>
          <input
            autoFocus
            required
            maxLength={160}
            value={displayName}
            placeholder="Social Media Agent"
            onChange={event => setDisplayName(event.target.value)}
          />
        </label>

        <label>
          <span>Agent key</span>
          <input
            maxLength={100}
            value={agentKey}
            placeholder="Auto-generated when empty"
            onChange={event => setAgentKey(event.target.value)}
          />
        </label>

        <label>
          <span>Department</span>
          <select
            value={department}
            onChange={event => setDepartment(event.target.value)}
          >
            <option value="general">General</option>
            <option value="marketing">Marketing</option>
            <option value="support">Customer Support</option>
            <option value="content">Content</option>
            <option value="analytics">Analytics</option>
          </select>
        </label>

        <label>
          <span>Requested risk</span>
          <select
            value={risk}
            onChange={event => setRisk(event.target.value)}
          >
            <option value="">Auto-detect</option>
            <option value="READ_ONLY">Read only</option>
            <option value="LOW">Low</option>
            <option value="HIGH">High</option>
            <option value="CRITICAL">Critical</option>
          </select>
        </label>
      </div>

      <label className="agent-builder-purpose">
        <span>Purpose</span>
        <textarea
          required
          minLength={20}
          maxLength={1000}
          rows={4}
          value={purpose}
          placeholder="Describe exactly what this agent should do and what it must never do."
          onChange={event => setPurpose(event.target.value)}
        />
      </label>

      <div className="agent-builder-field-grid">
        <label>
          <span>Allowed inputs</span>
          <input
            value={inputs}
            placeholder="published_article, campaign_plan"
            onChange={event => setInputs(event.target.value)}
          />
          <small>Comma-separated</small>
        </label>

        <label>
          <span>Requested tools</span>
          <input
            value={tools}
            placeholder="content_reader, analytics_reader"
            onChange={event => setTools(event.target.value)}
          />
          <small>Comma-separated</small>
        </label>

        <label>
          <span>Requested actions</span>
          <input
            value={actions}
            placeholder="prepare_social_drafts"
            onChange={event => setActions(event.target.value)}
          />
          <small>External actions increase risk automatically.</small>
        </label>

        <label>
          <span>Output fields</span>
          <input
            value={outputs}
            placeholder="drafts, channels, warnings"
            onChange={event => setOutputs(event.target.value)}
          />
          <small>Comma-separated</small>
        </label>
      </div>

      <label className="agent-builder-checkbox">
        <input
          type="checkbox"
          checked={readOnly}
          onChange={event => setReadOnly(event.target.checked)}
        />
        <span>
          <strong>Read-only design</strong>
          <small>No write or external execution capability requested.</small>
        </span>
      </label>

      <footer className="agent-builder-form-footer">
        <div>
          <strong>Preview only</strong>
          <span>
            No registry, runner, file, deployment or activation change.
          </span>
        </div>

        <button
          type="submit"
          className="primary-button"
          disabled={busy}
        >
          {busy ? "Generating brain…" : "Generate Brain Preview"}
        </button>
      </footer>
    </form>
  );
}
