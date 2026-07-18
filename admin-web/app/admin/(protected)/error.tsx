"use client";

export default function AdminError({ reset }: { reset: () => void }) {
  return <section className="state-panel error-state" role="alert"><strong>Admin panel could not be loaded.</strong><p>No sensitive error details are displayed.</p><button className="quiet-button" onClick={reset}>Try again</button></section>;
}
