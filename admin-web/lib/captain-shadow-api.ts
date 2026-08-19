import "server-only";

import { getAdminServerConfig } from "./server-config";

export type CaptainShadowAssessment = {
  mode: "CAPTAIN_SHADOW";
  decision: "APPROVE" | "WAIT" | "REJECT";
  direction: "BUY" | "SELL" | "NONE";
  confidence: number;
  live_cmp: string | null;
  buy_base: string | null;
  sell_base: string | null;
  targets: Array<string | null>;
  stop_loss: string | null;
  news_locked: boolean;
  macro_bias: string;
  macro_confidence: number;
  weekly: {
    trading_days: number;
    weekly_high: string;
    weekly_low: string;
    weekly_range: string;
    average_daily_range: string;
    higher_highs: number;
    lower_highs: number;
    higher_lows: number;
    lower_lows: number;
    bias: string;
  } | null;
  reasons: string[];
  read_only: boolean;
  signal_generated: boolean;
  delivery_started: boolean;
};

export type CaptainShadowState = {
  available: boolean;
  assessment: CaptainShadowAssessment | null;
};

export async function fetchCaptainShadow(
  token: string,
): Promise<CaptainShadowState> {
  if (!token) {
    return {
      available: false,
      assessment: null,
    };
  }

  try {
    const config = getAdminServerConfig();

    const response = await fetch(
      `${config.backendBaseUrl}/internal/captain/shadow`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Admin-BFF-Key": config.bffSecret,
        },
        cache: "no-store",
        signal: AbortSignal.timeout(15_000),
      },
    );

    if (!response.ok) {
      return {
        available: false,
        assessment: null,
      };
    }

    return {
      available: true,
      assessment:
        (await response.json()) as CaptainShadowAssessment,
    };
  } catch {
    return {
      available: false,
      assessment: null,
    };
  }
}
