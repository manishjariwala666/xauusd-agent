import type { Metadata } from "next";
import { configuredLinks } from "@/lib/site-config";

export const metadata: Metadata = { title: "Contact", description: "Configured public contact channels for VenusRealm." };

export default function ContactPage() {
  const links = configuredLinks();
  const channels = [["Telegram", links.telegram], ["WhatsApp", links.whatsapp], ["YouTube", links.youtube]].filter((entry): entry is [string, string] => Boolean(entry[1]));

  return <article className="content-page">
    <header className="content-page-header">
      <span className="eyebrow">CONTACT VENUSREALM</span>
      <h1>Reach the desk through a verified public channel.</h1>
      <p>Use only the destinations configured on this site. VenusRealm will never request your password, recovery phrase, private key or remote access to your device.</p>
    </header>

    {channels.length ? <div className="contact-hub">{channels.map(([label, href], index) => <a className="contact-channel" href={href} rel="noreferrer" target="_blank" key={label}>
      <small>0{index + 1} · VERIFIED CHANNEL</small>
      <h2>{label}</h2>
      <p>Open the configured public VenusRealm {label} destination in a new tab.</p>
      <strong>Open channel →</strong>
    </a>)}</div> : <div className="empty-state">No public contact channel is configured for this preview.</div>}

    <section className="contact-trust" aria-labelledby="contact-safety">
      <div><span className="eyebrow">ACCOUNT SAFETY</span><h2 id="contact-safety">Verify before you reply.</h2><p>Support should help you understand access, payments and platform navigation without asking for credentials or custody of funds.</p></div>
      <ul><li>Never share your account password or email verification token.</li><li>Never share wallet seed phrases or private keys.</li><li>Confirm payment and member-access instructions inside the VenusRealm member flow.</li><li>Report suspicious messages instead of continuing the conversation.</li></ul>
    </section>
  </article>;
}
