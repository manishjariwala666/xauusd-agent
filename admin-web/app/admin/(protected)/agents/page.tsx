import { cookies } from "next/headers";
import { AgentsDashboard } from "@/components/agents-dashboard";
import { fetchAdminAgents } from "@/lib/agents-api";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

export default async function AgentsPage() {
  const token = (await cookies()).get(ADMIN_SESSION_COOKIE)?.value || "";
  const data = await fetchAdminAgents(token);

  if (!data) {
    return (
      <section className="state-panel error-state">
        <strong>Agents could not be loaded.</strong>
        <p>Check the backend API connection and try again.</p>
      </section>
    );
  }

  return <AgentsDashboard data={data} />;
}
