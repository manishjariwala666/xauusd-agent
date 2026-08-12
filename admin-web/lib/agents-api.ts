import "server-only";

import { getAdminServerConfig } from "./server-config";

export type AgentRisk =
  | "READ_ONLY"
  | "LOW"
  | "MEDIUM"
  | "HIGH"
  | "CRITICAL"
  | "UNKNOWN";

export type CapabilityMode =
  | "READ"
  | "RUN"
  | "APPROVAL"
  | "BLOCKED";

export type AgentDashboardRecord = {
  agent_key: string;
  short_name: string;
  official_name: string;
  description: string;
  aliases: string[];
  run_action: string | null;
  brain_configured: boolean;
  can_toggle: boolean;
  purpose: string;
  default_risk: AgentRisk;
  automatic_actions: string[];
  approval_required_actions: string[];
  forbidden_actions: string[];
  output_schema: string[];
  capability_mode: CapabilityMode;
  capability_risk: AgentRisk;
  owner_approval_required: boolean;
  capability_allowed_actions: string[];
  capability_blocked_actions: string[];
  capability_dependencies: string[];
  is_configured: boolean;
  is_enabled: boolean | null;
  status: string;
  last_run_at: string | null;
  last_error: string;
  schedule_minutes: number | null;
  next_scheduled_run_at: string | null;
  success_count: number;
  failure_count: number;
  queue_size: number;
  last_duration_ms: number | null;
};

export type AgentsDashboardPayload = {
  items: AgentDashboardRecord[];
  count: number;
  read_only: boolean;
};

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];

  return value
    .filter((item): item is string => typeof item === "string")
    .map(item => item.trim())
    .filter(Boolean);
}

function finiteNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value)
    ? value
    : fallback;
}

function normalizeAgentDashboardRecord(
  value: unknown,
): AgentDashboardRecord | null {
  if (!value || typeof value !== "object") return null;

  const record = value as Record<string, unknown>;
  const agentKey = String(record.agent_key || "").trim();

  if (!agentKey) return null;

  const defaultRisk = String(record.default_risk || "UNKNOWN");
  const safeRisk: AgentRisk = [
    "READ_ONLY",
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
    "UNKNOWN",
  ].includes(defaultRisk)
    ? defaultRisk as AgentRisk
    : "UNKNOWN";

  const capabilityMode = String(
    record.capability_mode || "BLOCKED",
  );
  const safeCapabilityMode: CapabilityMode = [
    "READ",
    "RUN",
    "APPROVAL",
    "BLOCKED",
  ].includes(capabilityMode)
    ? capabilityMode as CapabilityMode
    : "BLOCKED";

  return {
    agent_key: agentKey,
    short_name: String(record.short_name || agentKey),
    official_name: String(record.official_name || agentKey),
    description: String(record.description || ""),
    aliases: stringList(record.aliases),
    run_action:
      typeof record.run_action === "string"
        ? record.run_action
        : null,
    brain_configured: record.brain_configured === true,
    can_toggle:
      agentKey === "ai_blog_agent" && record.can_toggle === true,
    purpose: String(record.purpose || record.description || ""),
    default_risk: safeRisk,
    automatic_actions: stringList(record.automatic_actions),
    approval_required_actions: stringList(
      record.approval_required_actions,
    ),
    forbidden_actions: stringList(record.forbidden_actions),
    output_schema: stringList(record.output_schema),
    capability_mode: safeCapabilityMode,
    capability_risk: [
      "READ_ONLY",
      "LOW",
      "MEDIUM",
      "HIGH",
      "CRITICAL",
      "UNKNOWN",
    ].includes(String(record.capability_risk || "UNKNOWN"))
      ? String(record.capability_risk) as AgentRisk
      : "UNKNOWN",
    owner_approval_required:
      record.owner_approval_required !== false,
    capability_allowed_actions: stringList(
      record.capability_allowed_actions,
    ),
    capability_blocked_actions: stringList(
      record.capability_blocked_actions,
    ),
    capability_dependencies: stringList(
      record.capability_dependencies,
    ),
    is_configured: record.is_configured === true,
    is_enabled:
      typeof record.is_enabled === "boolean"
        ? record.is_enabled
        : null,
    status: String(record.status || "NOT_CONFIGURED"),
    last_run_at:
      typeof record.last_run_at === "string"
        ? record.last_run_at
        : null,
    last_error: String(record.last_error || "").slice(0, 500),
    schedule_minutes:
      typeof record.schedule_minutes === "number" &&
      Number.isFinite(record.schedule_minutes)
        ? record.schedule_minutes
        : null,
    next_scheduled_run_at:
      typeof record.next_scheduled_run_at === "string"
        ? record.next_scheduled_run_at
        : null,
    success_count: finiteNumber(record.success_count),
    failure_count: finiteNumber(record.failure_count),
    queue_size: finiteNumber(record.queue_size),
    last_duration_ms:
      typeof record.last_duration_ms === "number" &&
      Number.isFinite(record.last_duration_ms)
        ? record.last_duration_ms
        : null,
  };
}

export function normalizeAgentsDashboardPayload(
  value: unknown,
): AgentsDashboardPayload | null {
  if (!value || typeof value !== "object") return null;

  const payload = value as Record<string, unknown>;
  if (!Array.isArray(payload.items)) return null;

  const items = payload.items
    .map(normalizeAgentDashboardRecord)
    .filter((item): item is AgentDashboardRecord => item !== null);

  return {
    items,
    count: finiteNumber(payload.count, items.length),
    read_only: payload.read_only !== false,
  };
}

export async function fetchAgentsDashboard(
  token: string,
): Promise<AgentsDashboardPayload | null> {
  if (!token) return null;

  try {
    const config = getAdminServerConfig();
    const response = await fetch(
      `${config.backendBaseUrl}/admin/agents`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Admin-BFF-Key": config.bffSecret,
        },
        cache: "no-store",
        signal: AbortSignal.timeout(8000),
      },
    );

    if (!response.ok) return null;

    return normalizeAgentsDashboardPayload(await response.json());
  } catch {
    return null;
  }
}
