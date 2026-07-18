import "server-only";

import { getAdminServerConfig } from "./server-config";

export type AdminUser = { user_id: number; email: string; role: "ADMIN" };
export type AdminSessionResult = {
  status: "authenticated" | "unauthenticated" | "forbidden" | "unavailable";
  user?: AdminUser;
};

export async function fetchAdminSession(token: string): Promise<AdminSessionResult> {
  if (!token) return { status: "unauthenticated" };
  try {
    const config = getAdminServerConfig();
    const response = await fetch(`${config.backendBaseUrl}/admin/auth/session`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Admin-BFF-Key": config.bffSecret
      },
      cache: "no-store",
      signal: AbortSignal.timeout(3000)
    });
    if (response.status === 401) return { status: "unauthenticated" };
    if (response.status === 403) return { status: "forbidden" };
    if (!response.ok) return { status: "unavailable" };
    const payload = (await response.json()) as { user?: AdminUser };
    if (!payload.user || payload.user.role !== "ADMIN") return { status: "forbidden" };
    return { status: "authenticated", user: payload.user };
  } catch {
    return { status: "unavailable" };
  }
}
