import type { Metadata } from "next";
import { LoginForm } from "@/components/login-form";

export const metadata: Metadata = { title: "Admin Sign In" };

export default function AdminLoginPage() {
  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-mark">VR</div>
        <small>SECURE ADMIN ACCESS</small>
        <h1>Welcome back</h1>
        <p>Use an approved, verified administrator account.</p>
        <LoginForm />
        <div className="security-note">Protected by short-lived sessions, CSRF validation and server-side role checks.</div>
      </section>
    </main>
  );
}
