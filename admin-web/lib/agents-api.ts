import "server-only";

import { getAdminServerConfig } from "./server-config";

export type AdminAgent = {
  agent_key: string;
  display_name: string;
  is_enabled: boolean;
  status: string;
  last_run_at: string | null;
  next_scheduled_run_at?: string | null;
  last_error: string | null;
  last_duration_ms?: number | null;
  success_count?: number;
  failure_count?: number;
  queue_size?: number;
};

export type AdminAgentRun = {
  id?: number;
  run_id?: number;
  agent_key?: string;
  display_name?: string;
  status?: string;
  started_at?: string | null;
  finished_at?: string | null;
  error_message?: string | null;
};

export type AdminAgentsData = {
  agents: AdminAgent[];
  runs: AdminAgentRun[];
};

export async function fetchAdminAgents(token: string): Promise<AdminAgentsData | null> {
  if (!token) return null;

  try {
    const config = getAdminServerConfig();
    const response = await fetch(`${config.backendBaseUrl}/admin/agents`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Admin-BFF-Key": config.bffSecret
      },
      cache: "no-store",
      signal: AbortSignal.timeout(5000)
    });

    if (!response.ok) return null;
    return await response.json() as AdminAgentsData;
  } catch {
    return null;
  }
}
