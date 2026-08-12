import "server-only";

export type AdminServerConfig = {
  backendBaseUrl: string;
  bffSecret: string;
};

export function getAdminServerConfig(): AdminServerConfig {
  const backendBaseUrl = (process.env.BACKEND_BASE_URL || "").trim().replace(/\/$/, "");
  const bffSecret = (process.env.ADMIN_BFF_SHARED_SECRET || "").trim();
  if (!backendBaseUrl || !bffSecret || bffSecret.length < 32) {
    throw new Error("Admin server authentication is not configured.");
  }
  return { backendBaseUrl, bffSecret };
}
