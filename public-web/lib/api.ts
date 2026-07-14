import { cache } from "react";
import type { Announcement, Category, ContentItem, PublicPage, Signal, SignalPage, VerifiedResult } from "./types";

const API_BASE = (
  process.env.BACKEND_BASE_URL ||
  "https://xauusd-agent-api-production.up.railway.app"
).replace(/\/$/, "");

async function fetchJson<T>(
  path: string,
  fallback: T,
  revalidate = 60
): Promise<T> {
  const attempts = revalidate > 0 ? 2 : 1;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2000);
    try {
      const response = await fetch(`${API_BASE}${path}`, {
        signal: controller.signal,
        next: { revalidate }
      });
      if (response.ok) return (await response.json()) as T;
    } catch {
      // Cacheable pages get one bounded retry before using their safe fallback.
    } finally {
      clearTimeout(timeout);
    }
  }
  return fallback;
}

export async function getCategories(): Promise<Category[]> {
  const response = await fetchJson<{ items: Category[] }>(
    "/public/categories",
    { items: [] },
    300
  );
  return response.items;
}

export async function getContent(
  contentType?: string,
  limit = 12
): Promise<ContentItem[]> {
  const query = new URLSearchParams({ limit: String(limit) });
  if (contentType) query.set("content_type", contentType);
  const response = await fetchJson<{ items: ContentItem[] }>(
    `/public/content?${query}`,
    { items: [] },
    300
  );
  return response.items;
}

async function fetchContentDetail(slug: string): Promise<ContentItem | null> {
  const response = await fetchJson<{ item: ContentItem | null }>(
    `/public/content/${encodeURIComponent(slug)}`,
    { item: null },
    300
  );
  return response.item;
}

// Metadata and page rendering request the same article. React cache guarantees
// that the API receives one detail request per render instead of two.
export const getContentDetail = cache(fetchContentDetail);

function normalizeSignal(signal: Signal): Signal {
  return { ...signal, direction: signal.direction || signal.signal_type, signal_type: signal.direction || signal.signal_type, entry_price: signal.entry_price ?? signal.price, price: signal.entry_price ?? signal.price, published_at: signal.published_at || signal.signal_time };
}

async function signalJson<T>(path: string): Promise<T | null> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 2000);
  try {
    const response = await fetch(`${API_BASE}${path}`, { signal: controller.signal, cache: "no-store" });
    return response.ok ? await response.json() as T : null;
  } catch { return null; }
  finally { clearTimeout(timeout); }
}

export async function getSignals(query = new URLSearchParams()): Promise<SignalPage> {
  const parameters = new URLSearchParams(query);
  parameters.set("page_size", "12");
  const current = await signalJson<SignalPage>(`/public/signals/v2?${parameters}`);
  if (current) return { ...current, items: current.items.map(normalizeSignal) };
  return { items: [], page: 1, page_size: 12, total: 0, pages: 1, fallback: true };
}

export async function getSignalDetail(publicId: string): Promise<Signal | null> {
  const response = await signalJson<{ item: Signal }>(`/public/signals/v2/${encodeURIComponent(publicId)}`);
  return response?.item ? normalizeSignal(response.item) : null;
}

export async function getSignalSnapshot(): Promise<Signal[]> {
  const response = await fetchJson<{ items: Signal[] }>(
    "/public/signals/v2?page_size=3",
    { items: [] },
    300
  );
  return response.items.map(normalizeSignal);
}
export async function getAnnouncements(query=new URLSearchParams()):Promise<PublicPage<Announcement>>{const p=new URLSearchParams(query);p.set("page_size","12");return fetchJson(`/public/announcements/v2?${p}`,{items:[],page:1,page_size:12,total:0,pages:1,fallback:true},120)}
async function announcementDetail(slug:string){const r=await fetchJson<{item:Announcement|null}>(`/public/announcements/v2/${encodeURIComponent(slug)}`,{item:null},120);return r.item}
export const getAnnouncementDetail=cache(announcementDetail);
export async function getResults(query=new URLSearchParams()):Promise<PublicPage<VerifiedResult>>{const p=new URLSearchParams(query);p.set("page_size","12");return fetchJson(`/public/results?${p}`,{items:[],page:1,page_size:12,total:0,pages:1,fallback:true},120)}
async function resultDetail(id:string){const r=await fetchJson<{item:VerifiedResult|null}>(`/public/results/${encodeURIComponent(id)}`,{item:null},120);return r.item}
export const getResultDetail=cache(resultDetail);
export async function getResultSnapshot():Promise<VerifiedResult[]>{const r=await fetchJson<PublicPage<VerifiedResult>>("/public/results?page_size=3",{items:[],page:1,page_size:3,total:0,pages:1},300);return r.items}

export function siteUrl(path = ""): string {
  const base = (process.env.NEXT_PUBLIC_SITE_URL || "https://venusrealm.net").replace(/\/$/, "");
  return `${base}/${path.replace(/^\//, "")}`;
}
