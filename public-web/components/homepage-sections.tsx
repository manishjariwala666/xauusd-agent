import Link from "next/link";
import { Icon, type IconName } from "@/components/icon";

export function SnapshotItem({ label, value, detail, href }: { label: string; value: string; detail: string; href?: string }) {
  const content = <><span>{label}</span><strong>{value}</strong><small>{detail}</small></>;
  return href ? <Link className="home-snapshot" href={href}>{content}</Link> : <div className="home-snapshot">{content}</div>;
}

export function ResearchToolCard({ icon, title, text, href }: { icon: IconName; title: string; text: string; href: string }) {
  return <Link className="home-tool-card" href={href}><span className="home-tool-icon"><Icon name={icon} /></span><h3>{title}</h3><p>{text}</p><span className="text-link">Explore <Icon name="arrow" size={16} /></span></Link>;
}

export function ProcessStep({ number, icon, title, text }: { number: string; icon: IconName; title: string; text: string }) {
  return <li><span className="home-process-number">{number}</span><span className="home-tool-icon"><Icon name={icon} /></span><h3>{title}</h3><p>{text}</p></li>;
}

export function InsightCard({ eyebrow, title, text }: { eyebrow: string; title: string; text: string }) {
  return <article className="home-insight-card"><span>{eyebrow}</span><h3>{title}</h3><p>{text}</p></article>;
}

export function FaqItem({ question, children }: { question: string; children: React.ReactNode }) {
  return <details className="home-faq-item"><summary>{question}<span aria-hidden="true">+</span></summary><p>{children}</p></details>;
}
