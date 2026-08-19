"use client";

export type BrainPreview = {
  state: string;
  agent_key: string;
  display_name: string;
  department: string;
  purpose: string;
  allowed_inputs: string[];
  allowed_tools: string[];
  automatic_actions: string[];
  approval_required_actions: string[];
  forbidden_actions: string[];
  output_schema: string[];
  default_risk: "READ_ONLY" | "LOW" | "HIGH" | "CRITICAL";
  execution_enabled: boolean;
  registry_written: boolean;
  runner_written: boolean;
  files_generated: boolean;
  owner_approval_required: boolean;
};

function humanize(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, letter => letter.toUpperCase());
}

function PreviewList({
  title,
  items,
}: {
  title: string;
  items: string[];
}) {
  return (
    <section className="agent-builder-preview-list">
      <h4>{title}</h4>
      {items.length ? (
        <ul>
          {items.map(item => (
            <li key={item}>{humanize(item)}</li>
          ))}
        </ul>
      ) : (
        <p>None configured.</p>
      )}
    </section>
  );
}

export function BrainPreviewCard({
  preview,
}: {
  preview: BrainPreview;
}) {
  return (
    <section className="agent-builder-preview">
      <header>
        <div>
          <span>BRAIN PREVIEW</span>
          <h3>{preview.display_name}</h3>
          <p>{preview.agent_key}</p>
        </div>

        <div className="agent-builder-preview-badges">
          <span
            className={`agent-risk agent-risk-${preview.default_risk
              .toLowerCase()
              .replaceAll("_", "-")}`}
          >
            {humanize(preview.default_risk)}
          </span>
          <span className="agent-builder-locked-badge">
            Execution locked
          </span>
        </div>
      </header>

      <div className="agent-builder-preview-summary">
        <div>
          <span>Department</span>
          <strong>{humanize(preview.department)}</strong>
        </div>
        <div>
          <span>Owner approval</span>
          <strong>
            {preview.owner_approval_required ? "Required" : "Not required"}
          </strong>
        </div>
        <div>
          <span>Registry written</span>
          <strong>{preview.registry_written ? "Yes" : "No"}</strong>
        </div>
        <div>
          <span>Files generated</span>
          <strong>{preview.files_generated ? "Yes" : "No"}</strong>
        </div>
      </div>

      <p className="agent-builder-preview-purpose">
        {preview.purpose}
      </p>

      <div className="agent-builder-preview-grid">
        <PreviewList title="Allowed inputs" items={preview.allowed_inputs} />
        <PreviewList title="Allowed tools" items={preview.allowed_tools} />
        <PreviewList
          title="Automatic actions"
          items={preview.automatic_actions}
        />
        <PreviewList
          title="Approval required"
          items={preview.approval_required_actions}
        />
        <PreviewList
          title="Forbidden actions"
          items={preview.forbidden_actions}
        />
        <PreviewList title="Output schema" items={preview.output_schema} />
      </div>

      <aside className="agent-builder-preview-warning">
        This is a design preview only. The agent cannot run, publish,
        deploy, send messages, modify production or write registry files.
      </aside>
    </section>
  );
}
