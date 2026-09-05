"use client";

import { useEffect } from "react";

const selector = [
  "main > section",
  ".home-page > section",
  ".content-page > section",
  ".signals-page > section",
  ".publication-page > section",
  ".content-card",
  ".publication-card",
  ".research-tool-card",
  ".premium-signal-card",
  ".astrology-info-card",
  ".astrology-notice-card",
  ".contact-channel",
  ".member-panel",
  ".deliverable-grid article",
  ".audience-grid article",
  ".stack-grid article",
  ".module-list a",
  ".editorial-faq details",
].join(",");

export function MotionReveal() {
  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const nodes = Array.from(document.querySelectorAll<HTMLElement>(selector));

    if (reduced || !("IntersectionObserver" in window)) {
      nodes.forEach((node) => node.classList.add("vr-reveal-ready"));
      return;
    }

    nodes.forEach((node, index) => {
      node.classList.add("vr-reveal");
      const isCard = node.matches("article, .content-card, .publication-card, .research-tool-card, .premium-signal-card, .contact-channel, .member-panel, .module-list a, .editorial-faq details");
      if (isCard) node.classList.add(index % 2 === 0 ? "vr-reveal-left" : "vr-reveal-right");
      else node.classList.add("vr-reveal-up");
      node.style.setProperty("--vr-reveal-delay", `${Math.min(index % 3, 2) * 35}ms`);
    });

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const target = entry.target as HTMLElement;
          target.classList.add("vr-reveal-ready");
          observer.unobserve(target);
        });
      },
      { rootMargin: "0px 0px -4% 0px", threshold: 0.1 },
    );

    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, []);

  return null;
}
