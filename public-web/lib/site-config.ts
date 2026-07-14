export type NavigationItem = { label: string; href: string };
export type SocialLink = NavigationItem & { external: true };

export const primaryNavigation: NavigationItem[] = [
  { label: "Home", href: "/" },
  { label: "Gold Signals", href: "/signals" },
  { label: "Market Analysis", href: "/category/analysis-department" },
  { label: "Astrology", href: "/astrology" },
  { label: "Learning", href: "/category/market-education" },
  { label: "Blog", href: "/blog" },
  { label: "Automation", href: "/automation-services" },
  { label: "About", href: "/about" }
];

function publicUrl(value: string | undefined): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.toString() : undefined;
  } catch {
    return undefined;
  }
}

export function configuredLinks() {
  return {
    admin: publicUrl(process.env.ADMIN_DASHBOARD_URL) || "https://venusrealm.net/admin?page=command-center",
    telegram: publicUrl(process.env.TELEGRAM_INVITE_URL),
    whatsapp: publicUrl(process.env.SUPPORT_WHATSAPP_URL),
    youtube: publicUrl(process.env.YOUTUBE_CHANNEL_URL),
    video: publicUrl(process.env.YOUTUBE_FEATURED_VIDEO_URL),
    facebook: publicUrl(process.env.FACEBOOK_URL),
    instagram: publicUrl(process.env.INSTAGRAM_URL),
    x: publicUrl(process.env.X_URL),
    linkedin: publicUrl(process.env.LINKEDIN_URL),
    reddit: publicUrl(process.env.REDDIT_URL),
    vk: publicUrl(process.env.VK_URL)
  };
}

export function configuredSocialLinks(): SocialLink[] {
  const links = configuredLinks();
  const candidates: [string, string | undefined][] = [
    ["Telegram", links.telegram], ["WhatsApp", links.whatsapp], ["YouTube", links.youtube],
    ["Facebook", links.facebook], ["Instagram", links.instagram], ["X", links.x],
    ["LinkedIn", links.linkedin], ["Reddit", links.reddit], ["VK", links.vk]
  ];
  return candidates.flatMap(([label, href]) => href ? [{ label, href, external: true as const }] : []);
}
