import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/api";
export default function robots(): MetadataRoute.Robots { const blocked = (process.env.BLOCK_SEARCH_INDEXING || "true").toLowerCase() !== "false"; return { rules: blocked ? { userAgent: "*", disallow: "/" } : { userAgent: "*", allow: "/", disallow: ["/admin"] }, sitemap: siteUrl("/sitemap.xml") }; }
