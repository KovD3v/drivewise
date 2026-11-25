/**
 * An external link the page may render: an absolute https URL, or null.
 * Source URLs come from catalogue data, so a `javascript:` or plain-http value never becomes an href.
 */
export function safeHttpsUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" ? parsed.href : null;
  } catch {
    return null;
  }
}
