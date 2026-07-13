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
  view_count?: number;
  schema_jsonld?: Record<string, unknown>;
};

export type Signal = {
  id?: number;
  symbol?: string;
  signal_type?: string;
  price?: number;
  target_1?: number;
  target_2?: number;
  target_3?: number;
  stop_loss?: number;
  signal_time?: string;
};
