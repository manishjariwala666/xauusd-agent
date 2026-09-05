import type { Metadata } from "next";
import Link from "next/link";
import { AutomationEnquiryForm } from "@/components/automation-enquiry-form";
import { Icon } from "@/components/icon";
import { siteUrl } from "@/lib/api";
import "./automation-services.css";

export const metadata: Metadata = { title: "AI Automation Services for Global Businesses", description: "Secure, human-approved AI agents, n8n workflows and business automation built around real operational needs.", alternates: { canonical: "/automation-services" }, openGraph: { title: "VenusRealm Automation Services", description: "Secure automation systems for worldwide businesses.", url: "/automation-services", type: "website" } };

const coreServices = [
  ["AI Agents","Approval-aware assistants for research, operations and knowledge work.",["Tool-connected workflows","Human review gates","Escalation paths","Audit-friendly outputs"]],
  ["Workflow Automation","Reliable n8n and API orchestration across business systems.",["CRM and lead routing","Email and calendar flows","Data validation","Failure handling"]],
  ["Messaging Automation","Policy-conscious Telegram and WhatsApp-compatible workflows.",["Approved alerts","Bot commands","Routing rules","Human handover"]]
];
const deliverables = [
  ["Architecture + workflow map","Documented systems, owners, approvals and failure paths."],
  ["Secure implementation","Least-privilege integrations built in a testable environment."],
  ["Testing + recovery plan","Normal, failure and rollback paths exercised before handover."],
  ["Documentation + runbooks","Operational notes for support, maintenance and future changes."],
  ["Monitoring foundation","Meaningful health and failure visibility where the stack supports it."],
  ["Handoff + support plan","Clear ownership after launch with optional ongoing optimization."]
];
const process = [
  ["Discovery","Clarify goals, constraints, owners and acceptable risk."],
  ["Architecture","Map systems, data, exceptions and approval points."],
  ["Build","Implement the workflow with scoped permissions and explicit controls."],
  ["Harden","Test failure, recovery and human-review paths before release."],
  ["Launch","Document, deploy and support a reversible production handover."]
];
const faqs = [["Which businesses do you work with?","Projects are evaluated by workflow fit, risk and operational value rather than geography or company size."],["Can existing tools be connected?","Often, yes. We first verify that each tool offers a safe supported API or integration path."],["Do you support WhatsApp and Telegram?","Yes, where official and policy-compliant integrations are available. External messages remain approval-aware."],["Is n8n required?","No. The architecture is selected for the project; n8n is one option, not a requirement."],["Can the system run on our server?","Self-hosted and customer-cloud options can be assessed during discovery."],["How is data protected?","Secrets stay server-side, access is scoped, and staging and audit controls are designed into the workflow."],["How long does a project take?","Timing depends on integrations, approvals and testing. A discovery review produces a realistic plan."],["Is ongoing support available?","Ongoing monitoring, maintenance and workflow optimization can be included in a tailored proposal."]];

export default function AutomationServicesPage() {
  const schema = { "@context":"https://schema.org", "@type":"Service", name:"Business Automation Services", provider:{"@type":"Organization",name:"VenusRealm",url:siteUrl()}, areaServed:"Worldwide", serviceType:"AI and business workflow automation", url:siteUrl("/automation-services") };
  const breadcrumb = { "@context":"https://schema.org", "@type":"BreadcrumbList", itemListElement:[{"@type":"ListItem",position:1,name:"Home",item:siteUrl()},{"@type":"ListItem",position:2,name:"Automation Services",item:siteUrl("/automation-services")}] };

  return <article className="automation-page">
    <script type="application/ld+json" dangerouslySetInnerHTML={{__html:JSON.stringify(schema)}}/>
    <script type="application/ld+json" dangerouslySetInnerHTML={{__html:JSON.stringify(breadcrumb)}}/>
    <nav className="breadcrumb" aria-label="Breadcrumb"><Link href="/">Home</Link><span>/</span><span>Automation Services</span></nav>

    <header className="svc-hero">
      <div><span className="svc-kicker">AI automation services</span><h1>Automation that <em>actually runs</em> in production.</h1><p>VenusRealm designs approval-aware AI agents, integrations and operational workflows around real business constraints—security, failure handling, permissions and human ownership included.</p><div className="svc-actions"><a className="svc-primary" href="#project-enquiry">Start a project</a><a className="svc-secondary" href="#core-services">Explore services</a></div></div>
      <aside className="svc-visual" aria-label="Automation architecture overview"><strong>From workflow map to controlled execution.</strong><div className="svc-map"><div className="svc-node"><Icon name="brain" size={26}/><b>AI agent</b></div><div className="svc-node center"><Icon name="shield" size={28}/><b>Approval layer</b></div><div className="svc-node"><Icon name="send" size={26}/><b>Delivery</b></div><div className="svc-node"><Icon name="chart" size={26}/><b>Data</b></div><div className="svc-node center"><Icon name="check" size={28}/><b>Validation</b></div><div className="svc-node"><Icon name="globe" size={26}/><b>APIs</b></div></div></aside>
    </header>

    <section id="core-services" className="svc-section"><div className="svc-heading"><span className="svc-kicker">What we offer</span><h2>Core automation categories</h2><p>Three focused service families, each scoped around reliability, security and measurable operational value.</p></div><div className="svc-core-grid">{coreServices.map(([title,text,items],index)=><article className="svc-card" key={String(title)}><span className="icon-wrap"><Icon name={index===0?"brain":index===1?"chart":"send"} size={21}/></span><h3>{title}</h3><p>{text}</p><ul>{(items as string[]).map(item=><li key={item}>{item}</li>)}</ul></article>)}</div></section>

    <section className="svc-deliverables"><div className="svc-heading"><span className="svc-kicker">Deliverables</span><h2>What you get</h2><p>Every engagement is structured around production-ready handoff, not just a demo.</p></div><div className="svc-deliverable-grid">{deliverables.map(([title,text],index)=><article key={title}><span className="icon-wrap"><Icon name={index%2===0?"check":"shield"} size={18}/></span><strong>{title}</strong><span>{text}</span></article>)}</div></section>

    <section className="svc-workflow"><div className="svc-heading"><span className="svc-kicker">Process</span><h2>Delivery workflow</h2><p>A clear path from operational problem to supported system.</p></div><div className="svc-flow">{process.map(([title,text],index)=><article className="svc-step" key={title}><span className="step-icon"><b>0{index+1}</b></span><h3>{title}</h3><p>{text}</p></article>)}</div></section>

    <section className="svc-architecture"><div><span className="svc-kicker">Architecture</span><h2>Built for reliability at scale</h2><p>Automation is only useful when it remains understandable, observable and reversible under real operating conditions.</p><ul><li>Security-first integration boundaries</li><li>Human approval for sensitive actions</li><li>Failure handling and recovery paths</li><li>Documented ownership after launch</li></ul></div><div className="arch-visual"><span>Input validation</span><span>Scoped API access</span><span>Approval checkpoints</span><span>Audit events</span><span>Retries + fallbacks</span><span>Operational handoff</span></div></section>

    <section className="svc-section"><div className="svc-heading"><span className="svc-kicker">Engagement</span><h2>How we can work together</h2><p>Flexible delivery models based on scope, integration risk and support needs.</p></div><div className="svc-engagement-grid"><article><h3>Focused build</h3><p>Best for one contained workflow with defined inputs and outcomes.</p><ul><li>Scoped implementation</li><li>Testing and documentation</li><li>Handoff session</li></ul><a href="#project-enquiry">Request scope →</a></article><article><h3>System build</h3><p>Best for multi-system automation or an AI assistant with production controls.</p><ul><li>Architecture + implementation</li><li>Security and failure review</li><li>Launch support</li></ul><a href="#project-enquiry">Discuss build →</a></article><article><h3>Ongoing optimization</h3><p>Best for systems that need maintenance, iteration and operational support.</p><ul><li>Monitoring review</li><li>Workflow changes</li><li>Priority maintenance</li></ul><a href="#project-enquiry">Discuss support →</a></article></div></section>

    <section className="svc-faq"><div className="svc-heading"><span className="svc-kicker">FAQ</span><h2>Common questions</h2></div>{faqs.map(([question,answer])=><details key={question}><summary>{question}<span>+</span></summary><p>{answer}</p></details>)}</section>

    <section id="project-enquiry" className="svc-enquiry"><div><span className="svc-kicker">Start a project</span><h2>Tell us where work is slowing your business down.</h2><p>Share enough context for a useful first review. Submission does not trigger automatic messages or create a contractual commitment.</p><ul><li>No file uploads</li><li>No credentials or confidential customer data</li><li>Human review before contact</li></ul></div><AutomationEnquiryForm/></section>

    <section className="svc-cta"><div><span className="svc-kicker">Ready to build?</span><h2>Start with the workflow that matters most.</h2></div><div className="svc-actions"><a className="svc-secondary" href="#project-enquiry">Start a project</a><Link className="svc-secondary" href="/contact">Contact VenusRealm</Link></div></section>
  </article>;
}
