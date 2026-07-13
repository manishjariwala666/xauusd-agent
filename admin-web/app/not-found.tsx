import Link from "next/link";

export default function NotFound() {
  return (
    <main className="centered-state">
      <div>
        <small>404</small>
        <h1>Admin page not found</h1>
        <p>This module is not available in Phase 1.</p>
        <Link className="primary-button" href="/admin/dashboard">Return to dashboard</Link>
      </div>
    </main>
  );
}
