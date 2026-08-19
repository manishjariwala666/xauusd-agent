import { cookies } from "next/headers";

import { AgentsDashboard } from "@/components/agents-dashboard";
import { fetchAgentsDashboard } from "@/lib/agents-api";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

export default async function AgentsPage() {
  const token =
    (await cookies()).get(ADMIN_SESSION_COOKIE)?.value || "";
  const data = await fetchAgentsDashboard(token);

  if (!data) {
    return (
      <section className="state-panel error-state">
        <strong>Agents could not be loaded.</strong>
        <p>
          The protected Agent Dashboard API is temporarily
          unavailable. No agent action was attempted.
        </p>
      </section>
    );
  }

  return <AgentsDashboard data={data} />;
}
