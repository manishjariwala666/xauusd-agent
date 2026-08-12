import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { SignalEditor } from "@/components/signal-editor";
import { fetchSignal } from "@/lib/signals-api";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

export default async function EditSignalPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) notFound();
  const token = (await cookies()).get(ADMIN_SESSION_COOKIE)?.value || "";
  const signal = await fetchSignal(id, token);
  if (!signal) notFound();
  return <SignalEditor initial={signal} />;
}
