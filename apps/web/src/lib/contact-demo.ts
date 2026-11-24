/**
 * Simulated contact submission. The Lovable design saved requests to Supabase
 * through a server function; this repo has no Supabase, so the form validates
 * and shows the receipt without sending or storing anything.
 */
import { responseDate } from "./contact-intelligence";
import { contactPayload, type ContactRequest } from "./contact-validation";

type ContactReceipt = ReturnType<typeof contactPayload> & { code: string; responseDate: string };

export async function submitContactDemo(
  data: ContactRequest,
): Promise<{ ok: true; receipt: ContactReceipt } | { ok: false; error: string }> {
  const payload = contactPayload(data);
  const code = `DEMO-${Math.random().toString(36).slice(2, 10).toUpperCase()}`;
  return { ok: true, receipt: { code, responseDate: responseDate(data.reason, new Date()), ...payload } };
}
