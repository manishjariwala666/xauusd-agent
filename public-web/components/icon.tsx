export type IconName = "arrow" | "book" | "brain" | "chart" | "check" | "clock" | "copy" | "globe" | "gold" | "menu" | "moon" | "send" | "shield" | "spark" | "target" | "x";

export function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  const paths: Record<IconName, React.ReactNode> = {
    arrow: <><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></>,
    book: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11v16H6.5A2.5 2.5 0 0 0 4 21.5z"/><path d="M20 5.5A2.5 2.5 0 0 0 17.5 3H13v16h4.5a2.5 2.5 0 0 1 2.5 2.5z"/></>,
    brain: <><path d="M9.5 4.5A3 3 0 0 0 5 7a3 3 0 0 0-1 5.8A3.5 3.5 0 0 0 9.5 18"/><path d="M14.5 4.5A3 3 0 0 1 19 7a3 3 0 0 1 1 5.8 3.5 3.5 0 0 1-5.5 5.2M12 3v18M8 9h4m4 6h-4"/></>,
    chart: <><path d="M4 20V10m6 10V4m6 16v-7m4 7H2"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    copy: <><rect x="8" y="8" width="11" height="11" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/></>,
    globe: <><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/></>,
    gold: <><path d="m4 15 3-7h10l3 7z"/><path d="M2 19h20M8 8l2-4h4l2 4"/></>,
    menu: <><path d="M4 7h16M4 12h16M4 17h16"/></>,
    moon: <path d="M20 15.5A8.5 8.5 0 0 1 8.5 4 8.5 8.5 0 1 0 20 15.5Z"/>,
    send: <><path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/></>,
    shield: <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/></>,
    spark: <><path d="m12 3-1.3 4.2L7 9l3.7 1.8L12 15l1.3-4.2L17 9l-3.7-1.8z"/><path d="m5 15-.7 2.3L2 18.5l2.3 1.2L5 22l.7-2.3 2.3-1.2-2.3-1.2z"/></>,
    target: <><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M12 3v3m9 6h-3m-6 9v-3M3 12h3"/></>,
    x: <><path d="M5 5l14 14M19 5 5 19"/></>
  };
  return <svg aria-hidden="true" className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}
