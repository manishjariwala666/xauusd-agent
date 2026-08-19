import { CaptainStatusPanel } from "@/components/captain-status-panel";
import { MasterAIConsole } from "@/components/master-ai-console";
import { MasterAIOperationsPanel } from "@/components/master-ai-operations-panel";

export default function AdminMasterAIPage() {
  return (
    <>
      <CaptainStatusPanel />
      <MasterAIOperationsPanel />
      <MasterAIConsole />
    </>
  );
}
