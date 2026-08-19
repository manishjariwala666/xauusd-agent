export function EmptyState({ title, message }: { title: string; message: string }) {
  return <section className="state-panel"><strong>{title}</strong><p>{message}</p></section>;
}

export function LoadingState() {
  return <section className="state-panel" aria-live="polite"><strong>Loading secure admin…</strong><p>Only the requested panel is being prepared.</p></section>;
}
