import { EmptyState } from "@/components/states";

const cards = [
  ["Content", "Not loaded", "Phase 2"],
  ["Signals", "Not loaded", "Phase 4"],
  ["Users", "Not loaded", "Phase 7"],
  ["Security", "Active", "Phase 1"]
];

export default function DashboardPage() {
  return (
    <>
      <section className="page-heading"><small>FOUNDATION STATUS</small><h1>Admin dashboard</h1><p>Lightweight secure shell. CMS, analytics, agents and operational data are intentionally not loaded.</p></section>
      <section className="kpi-grid" aria-label="Foundation KPI placeholders">
        {cards.map(([label, value, phase]) => <article className="kpi-card" key={label}><small>{label}</small><strong>{value}</strong><span>{phase}</span></article>)}
      </section>
      <EmptyState title="No Phase 1 activity feed" message="Operational modules will be connected only in their approved phases." />
    </>
  );
}
