export type Category = {
  id?: number;
  slug: string;
  title: string;
  description?: string;
  icon?: string;
  route_path?: string;
  meta_description?: string;
};

export type ContentItem = {
  id: number;
  content_type: string;
  slug: string;
  title: string;
  excerpt?: string;
  body?: string;
  image_url?: string;
  meta_title?: string;
  meta_description?: string;
  category_slug?: string;
  category_title?: string;
  subcategory?: string;
  published_at?: string;
  created_at?: string;
  updated_at?: string;
  author?: string;
  author_name?: string;
  view_count?: number;
  schema_jsonld?: Record<string, unknown>;
};

export type Signal = {
  id?: number;
  public_id?: string;
  symbol?: string;
  signal_type?: string;
  direction?: string;
  price?: number | string;
  entry_price?: number | string;
  entry_price_min?: number | string | null;
  entry_price_max?: number | string | null;
  entry_type?: string;
  target_1?: number | string | null;
  target_2?: number | string | null;
  target_3?: number | string | null;
  target_4?: number | string | null;
  stop_loss?: number | string | null;
  signal_time?: string;
  published_at?: string | null;
  updated_at?: string | null;
  timeframe?: string;
  status?: string;
  market?: string;
  risk_level?: string;
  confidence_label?: string | null;
  analysis_summary?: string | null;
  technical_reason?: string | null;
  astrology_reason?: string | null;
  risk_note?: string | null;
  outcome?: string | null;
};

export type SignalPage = { items: Signal[]; page: number; page_size: number; total: number; pages: number; fallback?: boolean };
