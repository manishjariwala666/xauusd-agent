const PRIVATE_IPV4 = /^(?:127\.|10\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.)/;

function isPrivateHostname(hostname: string): boolean {
  const normalized = hostname.toLowerCase();

  return (
    normalized === "localhost" ||
    normalized === "0.0.0.0" ||
    normalized === "::1" ||
    normalized.endsWith(".local") ||
    PRIVATE_IPV4.test(normalized)
  );
}

export function normalizeMediaUrl(
  value: unknown,
  backendBaseUrl: string,
  fallbackUrl: string,
): string {
  const raw = typeof value === "string" ? value.trim() : "";

  if (!raw || raw.startsWith("file:") || raw.startsWith("/tmp/")) {
    return fallbackUrl;
  }

  try {
    const backend = new URL(backendBaseUrl);
    const source = new URL(raw, backend);

    if (source.username || source.password) return fallbackUrl;
    if (source.pathname.startsWith("/media-local/")) return fallbackUrl;

    if (source.protocol === "https:" && !isPrivateHostname(source.hostname)) {
      return source.toString();
    }
  } catch {
    return fallbackUrl;
  }

  return fallbackUrl;
}

function normalizeMediaRecord(
  value: unknown,
  backendBaseUrl: string,
  fallbackUrl: string,
): unknown {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return value;
  }

  const record = value as Record<string, unknown>;
  if (!("public_url" in record) && !("thumbnail_url" in record)) {
    return value;
  }

  const mediaId = Number(record.id);
  const hasMediaId = Number.isInteger(mediaId) && mediaId > 0;
  const adminOrigin = new URL(fallbackUrl).origin;
  const originalBffUrl = hasMediaId
    ? new URL(`/api/admin/media-file/${mediaId}?variant=original`, adminOrigin).toString()
    : fallbackUrl;
  const thumbnailBffUrl = hasMediaId
    ? new URL(`/api/admin/media-file/${mediaId}?variant=thumbnail`, adminOrigin).toString()
    : fallbackUrl;

  // A durable storage URL is not necessarily public. Stream catalog records
  // through the authenticated BFF so private buckets work without exposing
  // storage credentials to the browser.
  const publicUrl = hasMediaId
    ? originalBffUrl
    : normalizeMediaUrl(record.public_url, backendBaseUrl, fallbackUrl);

  return {
    ...record,
    public_url: publicUrl,
    thumbnail_url: hasMediaId
      ? thumbnailBffUrl
      : normalizeMediaUrl(record.thumbnail_url, backendBaseUrl, fallbackUrl),
  };
}

export function normalizeMediaPayloadUrls(
  value: unknown,
  backendBaseUrl: string,
  fallbackUrl: string,
): unknown {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return value;
  }

  const payload = value as Record<string, unknown>;

  if (Array.isArray(payload.items)) {
    return {
      ...payload,
      items: payload.items.map(item =>
        normalizeMediaRecord(item, backendBaseUrl, fallbackUrl),
      ),
    };
  }

  return normalizeMediaRecord(value, backendBaseUrl, fallbackUrl);
}
