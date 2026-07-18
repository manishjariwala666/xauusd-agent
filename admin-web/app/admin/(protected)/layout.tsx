import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { AdminShell } from "@/components/admin-shell";
import { fetchAdminSession } from "@/lib/admin-api";
import { ADMIN_SESSION_COOKIE } from "@/lib/session";

export default async function ProtectedAdminLayout({ children }: { children: ReactNode }) {
  const token = (await cookies()).get(ADMIN_SESSION_COOKIE)?.value || "";
  const result = await fetchAdminSession(token);
  if (result.status === "forbidden") redirect("/admin/forbidden");
  if (result.status !== "authenticated" || !result.user) redirect("/admin/login");
  const localQa = process.env.ADMIN_LOCAL_QA_MODE === "true";
  return <AdminShell user={result.user} localQa={localQa}>{children}</AdminShell>;
}
