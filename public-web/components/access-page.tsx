import Link from "next/link";
import { Icon } from "./icon";
import { configuredLinks } from "@/lib/site-config";

export function AccessPage({ mode }: { mode: "login" | "signup" | "forgot" | "reset" }) {
  const admin = configuredLinks().admin;
  const copy = {
    login: ["ADMIN ACCESS", "Continue to secure login", "Authentication is handled by the existing protected admin service. Public-web does not collect or store your credentials."],
    signup: ["ACCOUNT REGISTRATION", "Public signup is not available", "No public registration workflow is enabled in this phase. An account form is intentionally not shown."],
    forgot: ["ACCOUNT RECOVERY", "Use the protected login service", "Password recovery is managed by the existing authentication service, not this public preview."],
    reset: ["PASSWORD RESET", "Reset links open in the protected service", "This preview does not process password-reset tokens or credentials."]
  }[mode];
  return <article className="auth-card"><span className="eyebrow">{copy[0]}</span><h1>{copy[1]}</h1><p>{copy[2]}</p><div className="auth-actions"><a className="button button-dark" href={admin}>Open secure admin login <Icon name="arrow" size={18}/></a><Link className="button" href="/">Return home</Link></div></article>;
}
