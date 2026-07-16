type FetchImplementation = (
  input: string | URL | Request,
  init?: RequestInit,
) => Promise<Response>;

export type EnquiryProxyResult = {
  status: number;
  payload: Record<string, unknown>;
};

const INVALID_RESPONSE_MESSAGE =
  "Enquiry service returned an invalid response.";
const UNAVAILABLE_MESSAGE =
  "Enquiry service is temporarily unavailable.";

function isJsonObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function safeUpstreamStatus(status: number): number {
  return Number.isInteger(status) && status >= 400 && status <= 599
    ? status
    : 502;
}

export async function proxyAutomationEnquiry({
  backendBaseUrl,
  body,
  forwardedFor,
  fetchImplementation = fetch,
}: {
  backendBaseUrl: string;
  body: string;
  forwardedFor: string;
  fetchImplementation?: FetchImplementation;
}): Promise<EnquiryProxyResult> {
  let upstream: Response;

  try {
    upstream = await fetchImplementation(
      `${backendBaseUrl.replace(/\/$/, "")}/public/automation-enquiries`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Forwarded-For": forwardedFor,
        },
        body,
        cache: "no-store",
        signal: AbortSignal.timeout(5_000),
      },
    );
  } catch {
    return {
      status: 503,
      payload: { message: UNAVAILABLE_MESSAGE },
    };
  }

  let payload: unknown;

  try {
    payload = JSON.parse(await upstream.text());
  } catch {
    return {
      status: safeUpstreamStatus(upstream.status),
      payload: { message: INVALID_RESPONSE_MESSAGE },
    };
  }

  if (!isJsonObject(payload)) {
    return {
      status: safeUpstreamStatus(upstream.status),
      payload: { message: INVALID_RESPONSE_MESSAGE },
    };
  }

  return {
    status: upstream.status,
    payload,
  };
}
