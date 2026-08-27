"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { Signal } from "@/lib/types";

const value = (input?: number | string | null) => input == null || input === "" ? "—" : String(input);

export function MemberSignalDetail({ publicId }: { publicId: string }) {
  const [signal, setSignal] = useState<Signal | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "auth" | "payment" | "missing" | "error">("loading");

  useEffect(() => {
    let active = true;
    void (async () => {
      const response = await fetch(`/api/member/signals/${encodeURIComponent(publicId)}`, { cache: "no-store" });
      if (!active) return;
      if (response.status === 401) return setState("auth");
      if (response.status === 403) return setState("payment");
      if (response.status === 404) return setState("missing");
      if (!response.ok) return setState("error");
      const data = await response.json() as { item?: Signal };
      setSignal(data.item || null);
      setState(data.item ? "ready" : "missing");
    })();
    return () => { active = false; };
  }, [publicId]);

  if (state === "loading") return <section><p>Checking protected member access…</p></section>;
  if (state === "auth") return <section><h2>Member login required</h2><p>This signal detail is not exposed publicly.</p><Link className="button primary" href="/login">Member login</Link></section>;
  if (state === "payment") return <section><h2>Verified paid membership required</h2><p>Complete payment verification from the Gold Signals member panel.</p><Link className="button primary" href="/signals">Open member access</Link></section>;
  if (state === "missing") return <section><h2>Signal unavailable</h2><p>The requested signal is not published or no longer available.</p></section>;
  if (state === "error" || !signal) return <section><h2>Signal temporarily unavailable</h2><p>Please try again from the member signal feed.</p></section>;

  return <>
    <section aria-labelledby="signal-levels"><h2 id="signal-levels">Protected signal levels</h2><dl><div><dt>Direction</dt><dd>{signal.direction || signal.signal_type || "—"}</dd></div><div><dt>Entry</dt><dd>{value(signal.entry_price)}</dd></div><div><dt>Entry range</dt><dd>{value(signal.entry_price_min)} – {value(signal.entry_price_max)}</dd></div><div><dt>Stop loss</dt><dd>{value(signal.stop_loss)}</dd></div><div><dt>Target 1</dt><dd>{value(signal.target_1)}</dd></div><div><dt>Target 2</dt><dd>{value(signal.target_2)}</dd></div><div><dt>Target 3</dt><dd>{value(signal.target_3)}</dd></div><div><dt>Target 4</dt><dd>{value(signal.target_4)}</dd></div></dl></section>
    <section aria-labelledby="signal-analysis"><h2 id="signal-analysis">Member analysis</h2><p>{signal.analysis_summary || "No additional published analysis is available for this signal."}</p></section>
  </>;
}
