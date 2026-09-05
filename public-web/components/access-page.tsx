import Link from "next/link";
import { Suspense } from "react";
import { MemberAccessForm, type MemberAccessMode } from "./member-access-form";
import styles from "./access-page.module.css";

const content: Record<MemberAccessMode, { eyebrow: string; title: string; accent: string; intro: string }> = {
  login: {
    eyebrow: "Secure member access",
    title: "Welcome back to",
    accent: "VenusRealm.",
    intro: "Sign in to your verified member account to review payment status, protected Gold Signals and available private-channel access.",
  },
  signup: {
    eyebrow: "Member registration",
    title: "Create your",
    accent: "VenusRealm account.",
    intro: "Register, verify your email and submit your payment reference for manual review. Premium access remains locked until verification is complete.",
  },
  forgot: {
    eyebrow: "Account recovery",
    title: "Recover your",
    accent: "member access.",
    intro: "Enter the email linked to your membership. If the account exists, we’ll send a secure password-reset link.",
  },
  reset: {
    eyebrow: "Password reset",
    title: "Set a new",
    accent: "secure password.",
    intro: "Choose a new password using the secure reset link from your email. Reset links are single-use and expire.",
  },
  verify: {
    eyebrow: "Email verification",
    title: "Verify your",
    accent: "member email.",
    intro: "Confirm the secure verification token from your email before signing in to your VenusRealm account.",
  },
};

export function AccessPage({ mode }: { mode: MemberAccessMode }) {
  const copy = content[mode];
  const isLogin = mode === "login";

  return (
    <section className={styles.page} aria-labelledby="member-access-title">
      <div className={styles.story}>
        <span className="eyebrow">{copy.eyebrow}</span>
        <h1 id="member-access-title">{copy.title} <em>{copy.accent}</em></h1>
        <p className={styles.storyLead}>{copy.intro}</p>

        <div className={styles.optionGrid} aria-label="Member access benefits">
          <div className={styles.optionCard}>
            <span className={styles.optionIcon}>01</span>
            <div><strong>Protected Gold Signals</strong><span>Actionable levels remain available only through verified member access.</span></div>
            <span className={styles.optionArrow} aria-hidden="true">→</span>
          </div>
          <div className={styles.optionCard}>
            <span className={styles.optionIcon}>02</span>
            <div><strong>Payment & access status</strong><span>Review verification status and submit your payment reference securely.</span></div>
            <span className={styles.optionArrow} aria-hidden="true">→</span>
          </div>
          <div className={styles.optionCard}>
            <span className={styles.optionIcon}>03</span>
            <div><strong>Private member channels</strong><span>Approved members can access configured private Telegram or WhatsApp channels.</span></div>
            <span className={styles.optionArrow} aria-hidden="true">→</span>
          </div>
        </div>

        <div className={styles.trustRow}>
          <span>Secure session cookie</span>
          <span>Manual payment verification</span>
          <span>Risk-first access controls</span>
        </div>
      </div>

      <div className={styles.formShell}>
        <div className={styles.formPanel}>
          <span className="eyebrow">{isLogin ? "Sign in" : copy.eyebrow}</span>
          <h2>{isLogin ? "Access your account" : copy.title}</h2>
          <p className={styles.formIntro}>{isLogin ? "Use the email and password linked to your verified VenusRealm membership." : copy.intro}</p>

          <Suspense fallback={<p>Loading secure member form…</p>}>
            <MemberAccessForm mode={mode} />
          </Suspense>

          <div className={styles.formFooter}>
            <Link href="/">← Return to VenusRealm</Link>
            <span>Premium access unlocks only after verification.</span>
          </div>
        </div>
      </div>
    </section>
  );
}
