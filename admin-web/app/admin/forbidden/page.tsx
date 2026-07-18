import Link from "next/link";

export default function ForbiddenPage() {
  return (
    <main className="auth-page">
      <section className="auth-card state-card">
        <div className="auth-mark warning">!</div>
        <small>ACCESS DENIED</small>
        <h1>Administrator approval required</h1>
        <p>This area is available only to verified and approved administrators.</p>
        <Link className="primary-button link-button" href="/admin/login">Return to sign in</Link>
      </section>
    </main>
  );
}
