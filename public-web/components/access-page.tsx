import Link from "next/link";
import { MemberAccessForm, type MemberAccessMode } from "./member-access-form";

export function AccessPage({ mode }: { mode: MemberAccessMode }) {
  const copy = {
    login: ["MEMBER ACCESS", "Sign in to VenusRealm", "Use your verified member account. Paid Gold Signal access remains locked until payment status is VERIFIED."],
    signup: ["MEMBER REGISTRATION", "Create your VenusRealm account", "Register as a member, verify your email, then submit your USDT transaction for manual review."],
    forgot: ["ACCOUNT RECOVERY", "Reset your password", "Enter your member email. If the account exists, a secure reset link will be sent."],
    reset: ["PASSWORD RESET", "Choose a new password", "Use the secure reset token from your email. Reset tokens are single-use and expire."],
    verify: ["EMAIL VERIFICATION", "Verify your member email", "Confirm the verification token from your email before signing in."],
  }[mode];

  return <article className="auth-card">
    <span className="eyebrow">{copy[0]}</span>
    <h1>{copy[1]}</h1>
    <p>{copy[2]}</p>
    <MemberAccessForm mode={mode} />
    <div className="auth-actions"><Link className="button" href="/">Return home</Link></div>
  </article>;
}
