import "server-only";

import { getAdminServerConfig } from "./server-config";

export type AdminUser = { user_id: number; email: string; role: "ADMIN" };
export type AdminSessionResult = {
  status: "authenticated" | "unauthenticated" | "forbidden" | "unavailable";
  user?: AdminUser;
};

type BackendErrorPayload = { detail?: string };

async function readBackendError(response: Response): Promise<string> {
  try {
    const payload = (await response.clone().json()) as BackendErrorPayload;
    return String(payload.detail || "").trim();
  } catch {
    return "";
  }
}

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
      signal: AbortSignal.timeout(10000)
    });
    if (response.status === 401) return { status: "unauthenticated" };
    if (response.status === 403) {
      const detail = await readBackendError(response);
      if (detail === "Administrator access is forbidden.") {
        return { status: "forbidden" };
      }
      // A BFF secret/configuration mismatch is infrastructure failure, not an
      // account approval denial. Preserve the cookie and surface retry state.
      return { status: "unavailable" };
    }
    if (!response.ok) return { status: "unavailable" };
    const payload = (await response.json()) as { user?: AdminUser };
    if (!payload.user || payload.user.role !== "ADMIN") return { status: "forbidden" };
    return { status: "authenticated", user: payload.user };
  } catch {
    return { status: "unavailable" };
  }
}
