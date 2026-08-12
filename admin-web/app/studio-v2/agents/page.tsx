import { cookies } from "next/headers";

import { AgentsDashboard } from "@/components/agents-dashboard";
import { fetchAgentsDashboard } from "@/lib/agents-api";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

export default async function StudioAgentsPage() {
  const token =
    (await cookies()).get(ADMIN_SESSION_COOKIE)?.value || "";

  const data = await fetchAgentsDashboard(token);

  if (!data) {
    return (
      <main className="studio-v2-module-page">
        <span className="section-kicker">
          AUTOMATION
        </span>

        <h1>Agent Workspace</h1>

        <p>
          Registered agent information could not be loaded
          from the local staging backend.
        </p>

        <section
          className="studio-v2-module-placeholder"
          role="alert"
        >
          <strong>Agent registry unavailable</strong>
          <p>
            No agents were started, stopped, deployed or modified.
          </p>
        </section>
      </main>
    );
  }

  return (
    <main className="studio-v2-agents-page">
      <AgentsDashboard data={data} />
    </main>
  );
}
