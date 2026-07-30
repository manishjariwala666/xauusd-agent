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
