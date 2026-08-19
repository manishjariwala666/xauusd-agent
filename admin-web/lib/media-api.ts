import "server-only";

import { getAdminServerConfig } from "./server-config";
import type { Paginated } from "./content-api";

export type MediaAsset = {
  id: number; storage_provider: "LOCAL" | "SUPABASE"; bucket: string;
  storage_path: string; thumbnail_path: string | null; public_url: string;
  thumbnail_url: string | null; original_filename: string; stored_filename: string;
  mime_type: string; size_bytes: number; width: number; height: number;
  alt_text: string; caption: string; source_type: string;
  uploaded_by_email: string | null; created_at: string; updated_at: string;
  deleted_at: string | null; usage_count: number; published_usage_count: number;
};

export async function fetchMediaList(query: URLSearchParams, token: string) {
  if (!token) return null;
  try {
    const config = getAdminServerConfig();
    const response = await fetch(`${config.backendBaseUrl}/admin/media?${query}`, {
      headers: { Authorization: `Bearer ${token}`, "X-Admin-BFF-Key": config.bffSecret },
      cache: "no-store", signal: AbortSignal.timeout(5000)
    });
    if (!response.ok) return null;
    return await response.json() as Paginated<MediaAsset>;
  } catch { return null; }
}
