import { createServerFn } from "@tanstack/react-start";
import { getRequest } from "@tanstack/react-start/server";
import { contactPayload, contactRequestSchema, contactSubmissionAllowed } from "./contact-validation";
import { responseDate } from "./contact-intelligence";

export const submitContact = createServerFn({ method: "POST" })
  .validator((input: unknown) => contactRequestSchema.parse(input))
  .handler(async ({ data }) => {
    const request = getRequest();
    const origin = request.headers.get("origin");
    if ((origin && origin !== new URL(request.url).origin) || request.headers.get("sec-fetch-site") === "cross-site" || !contactSubmissionAllowed(data.website)) {
      return { ok: false, error: "Non è stato possibile inviare la richiesta." } as const;
    }
    const payload = contactPayload(data);
    const due = responseDate(data.reason, new Date());
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { data: code, error } = await supabaseAdmin.rpc("submit_contact_request", { p_email: data.email, p_payload: payload, p_due: due });
    if (error || !code) return { ok: false, error: "Non è stato possibile registrare la richiesta. Riprova più tardi o scrivici via email." } as const;
    return { ok: true, receipt: { code, responseDate: due, ...payload } } as const;
  });