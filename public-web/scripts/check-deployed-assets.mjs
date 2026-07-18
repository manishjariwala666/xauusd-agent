import { verifyHomepageAssets } from "../lib/deployed-asset-health.mjs";

const baseUrl = process.argv.slice(2).find((argument) => argument !== "--") || process.env.NETLIFY_ASSET_CHECK_URL;
if (!baseUrl) {
  console.error("Usage: pnpm verify:assets -- https://example.netlify.app");
  process.exit(2);
}

try {
  const result = await verifyHomepageAssets({ baseUrl });
  console.log(`Homepage HTTP ${result.homepageStatus}; ${result.assets.length} referenced CSS/JS assets returned 200.`);
} catch (error) {
  console.error(error instanceof Error ? error.message : "Asset verification failed.");
  process.exit(1);
}
