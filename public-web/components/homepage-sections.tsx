import Link from "next/link";
import { Icon, type IconName } from "./icon";

export function InsightCard({ index, label, value }: { index: string; label: string; value: string }) {
  return <div><span>{index}</span><small>{label}</small><strong>{value}</strong></div>;
}

export function SnapshotItem({ label, value, detail, href }: { label: string; value: string; detail: string; href?: string }) {
  const content = <><small>{label}</small><strong>{value}</strong><span>{detail}</span></>;
  return href ? <Link className="desk-snapshot" href={href}>{content}</Link> : <div className="desk-snapshot">{content}</div>;
}

export function ResearchToolCard({ icon, title, text, href, index }: { icon: IconName; title: string; text: string; href: string; index: number }) {
  const content = <><div className="tool-card-top"><span>0{index}</span><Icon name={icon} size={22} /></div><h3>{title}</h3><p>{text}</p><span className="tool-card-link">Explore <Icon name="arrow" size={15} /></span></>;
  return href.startsWith("http") ? <a className="research-tool-card" href={href} rel="noreferrer" target="_blank">{content}</a> : <Link className="research-tool-card" href={href}>{content}</Link>;
}

export function ProcessStep({ number, icon, title, text }: { number: string; icon: IconName; title: string; text: string }) {
  return <li><div><span>{number}</span><Icon name={icon} size={21} /></div><h3>{title}</h3><p>{text}</p></li>;
}

export function FaqItem({ number, question, children }: { number: string; question: string; children: React.ReactNode }) {
  return <details><summary><span>{number}</span><strong>{question}</strong><i aria-hidden="true">+</i></summary><p>{children}</p></details>;
}

