import { cookies } from "next/headers";

import { AgentApprovalCenter } from "@/components/agent-approval-center";
import { fetchAgentsDashboard } from "@/lib/agents-api";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

export default async function StudioApprovalsPage() {
  const token =
    (await cookies()).get(ADMIN_SESSION_COOKIE)?.value ||
    "";

  const data = await fetchAgentsDashboard(token);

  if (!data) {
    return (
      <main className="studio-v2-module-page">
        <section className="state-panel error-state">
          <strong>
            Approval registry unavailable
          </strong>
          <p>
            No approval, agent, publishing or messaging
            action was attempted.
          </p>
        </section>
      </main>
    );
  }

  return <AgentApprovalCenter data={data} />;
}
