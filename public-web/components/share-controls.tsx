"use client";

import { useState } from "react";
import { Icon } from "./icon";

export function ShareControls({ title, url }: { title: string; url: string }) {
  const [copied, setCopied] = useState(false);
  const encodedUrl = encodeURIComponent(url);
  const encodedTitle = encodeURIComponent(title);
  const shares = [
    ["WhatsApp", `https://wa.me/?text=${encodedTitle}%20${encodedUrl}`],
    ["Telegram", `https://t.me/share/url?url=${encodedUrl}&text=${encodedTitle}`],
    ["Facebook", `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`],
    ["X", `https://x.com/intent/post?url=${encodedUrl}&text=${encodedTitle}`],
    ["LinkedIn", `https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`],
    ["Reddit", `https://www.reddit.com/submit?url=${encodedUrl}&title=${encodedTitle}`],
    ["VK", `https://vk.com/share.php?url=${encodedUrl}&title=${encodedTitle}`]
  ];
  async function share() {
    try {
      if (navigator.share) await navigator.share({ title, url });
      else await copy();
    } catch { /* A cancelled native share needs no error UI. */ }
  }
  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch { setCopied(false); }
  }
  return <aside className="share-controls" aria-label="Share this article"><span>Share</span><div className="share-links">{shares.map(([label, href]) => <a href={href} key={label} aria-label={`Share on ${label}`} rel="noreferrer" target="_blank">{label.slice(0, 2)}</a>)}<button type="button" onClick={copy} aria-label="Copy article link"><Icon name={copied ? "check" : "copy"} size={16} /></button><button className="native-share" type="button" onClick={share} aria-label="Open share menu"><Icon name="send" size={16} /></button></div><small aria-live="polite">{copied ? "Copied" : ""}</small></aside>;
}
