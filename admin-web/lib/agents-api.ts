import "server-only";

import { getAdminServerConfig } from "./server-config";

export type AgentRisk =
  | "READ_ONLY"
  | "LOW"
  | "HIGH"
  | "CRITICAL"
  | "UNKNOWN";

export type AgentDashboardRecord = {
  agent_key: string;
  short_name: string;
  official_name: string;
  description: string;
  aliases: string[];
  run_action: string | null;
  brain_configured: boolean;
  purpose: string;
  default_risk: AgentRisk;
  automatic_actions: string[];
  approval_required_actions: string[];
  forbidden_actions: string[];
  output_schema: string[];
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

    const payload =
      (await response.json()) as AgentsDashboardPayload;

    if (
      !Array.isArray(payload.items) ||
      typeof payload.count !== "number"
    ) {
      return null;
    }

    return payload;
  } catch {
    return null;
  }
}
