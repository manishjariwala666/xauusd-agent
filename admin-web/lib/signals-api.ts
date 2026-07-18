import "server-only";

import { getAdminServerConfig } from "./server-config";

export type AdminSignal = {
  id: number; public_id: string; symbol: string; market: string;
  signal_type: "BUY" | "SELL"; timeframe: string; entry_type: string;
  price: string; entry_price_min: string | null; entry_price_max: string | null;
  stop_loss: string | null; target_1: string | null; target_2: string | null;
  target_3: string | null; target_4: string | null; risk_level: string;
  confidence_label: string | null; analysis_summary: string | null;
  technical_reason: string | null; astrology_reason: string | null; risk_note: string | null;
  publication_status: string; lifecycle_status: string; published_at: string | null;
  scheduled_at: string | null; expires_at: string | null; closed_at: string | null;
  featured: boolean; updated_at: string;
};

export type SignalStats = Record<string, number> & { total: number };
export type SignalsPage = { items: AdminSignal[]; page: number; page_size: number; total: number; pages: number; stats: SignalStats };

async function adminSignalFetch<T>(path: string, token: string): Promise<T | null> {
  if (!token) return null;
  try {
    const config = getAdminServerConfig();
    const response = await fetch(`${config.backendBaseUrl}/admin/signals${path}`, {
      headers: { Authorization: `Bearer ${token}`, "X-Admin-BFF-Key": config.bffSecret },
      cache: "no-store", signal: AbortSignal.timeout(5000)
    });
    if (!response.ok) return null;
    return await response.json() as T;
  } catch { return null; }
}

export function fetchSignals(query: URLSearchParams, token: string) {
  return adminSignalFetch<SignalsPage>(`?${query}`, token);
}

export function fetchSignal(id: string, token: string) {
  return adminSignalFetch<AdminSignal>(`/${encodeURIComponent(id)}`, token);
}
