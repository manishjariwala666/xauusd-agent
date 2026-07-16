const ASSET_PATTERN = /(?:href|src)=["']([^"']+\.(?:css|js)(?:\?[^"']*)?)["']/gi;

export function extractReferencedAssets(html, baseUrl) {
  const assets = new Set();
  for (const match of html.matchAll(ASSET_PATTERN)) {
    assets.add(new URL(match[1], baseUrl).href);
  }
  return [...assets];
}

export async function verifyHomepageAssets({ baseUrl, fetchImplementation = fetch }) {
  const homepageUrl = new URL("/", baseUrl).href;
  const homepage = await fetchImplementation(homepageUrl, { redirect: "follow" });
  if (!homepage.ok) {
    throw new Error(`Homepage returned HTTP ${homepage.status}.`);
  }

  const assets = extractReferencedAssets(await homepage.text(), homepageUrl);
  if (assets.length === 0) {
    throw new Error("Homepage did not reference any CSS or JavaScript assets.");
  }

  const results = await Promise.all(
    assets.map(async (url) => {
      const response = await fetchImplementation(url, { redirect: "follow" });
      return { url, status: response.status, ok: response.ok };
    }),
  );
  const failures = results.filter((result) => !result.ok);
  if (failures.length > 0) {
    const summary = failures.map(({ url, status }) => `${new URL(url).pathname}: ${status}`).join(", ");
    throw new Error(`Referenced assets failed: ${summary}`);
  }

  return { homepageStatus: homepage.status, assets: results };
}
