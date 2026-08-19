export async function readMediaResponse<T>(response: Response): Promise<T> {
  const text = await response.text();

  if (!text) {
    throw new Error(`Media service returned an empty response (HTTP ${response.status}).`);
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`Media service returned an invalid response (HTTP ${response.status}).`);
  }
}
