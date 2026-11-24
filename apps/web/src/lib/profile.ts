/** Profilo utente: nome mostrato, consensi privacy e preferenze email. */
import { supabase } from "@/integrations/supabase/client";

export type Profile = {
  id: string;
  displayName: string | null;
  privacyConsentAt: string | null;
  marketingEmailsOptIn: boolean;
  marketingConsentAt: string | null;
};

function map(row: {
  id: string;
  display_name: string | null;
  privacy_consent_at: string | null;
  marketing_emails_opt_in: boolean;
  marketing_consent_at: string | null;
}): Profile {
  return {
    id: row.id,
    displayName: row.display_name,
    privacyConsentAt: row.privacy_consent_at,
    marketingEmailsOptIn: row.marketing_emails_opt_in,
    marketingConsentAt: row.marketing_consent_at,
  };
}

/** Legge il profilo dell'utente corrente, creandolo se manca. */
export async function getMyProfile(userId: string): Promise<Profile | null> {
  const { data, error } = await supabase
    .from("profiles")
    .select("id, display_name, privacy_consent_at, marketing_emails_opt_in, marketing_consent_at")
    .eq("id", userId)
    .maybeSingle();
  if (error) throw new Error(error.message);
  if (data) return map(data);

  const { data: created, error: insertError } = await supabase
    .from("profiles")
    .insert({ id: userId })
    .select("id, display_name, privacy_consent_at, marketing_emails_opt_in, marketing_consent_at")
    .maybeSingle();
  if (insertError) throw new Error(insertError.message);
  return created ? map(created) : null;
}

/** Salva il nome scelto e registra l'accettazione di privacy e termini. */
export async function completeOnboarding(userId: string, displayName: string): Promise<Profile> {
  const { data, error } = await supabase
    .from("profiles")
    .update({
      display_name: displayName.trim(),
      privacy_consent_at: new Date().toISOString(),
    })
    .eq("id", userId)
    .select("id, display_name, privacy_consent_at, marketing_emails_opt_in, marketing_consent_at")
    .single();
  if (error) throw new Error(error.message);
  return map(data);
}

/** Aggiorna il consenso alle email su novità, con il timestamp della modifica. */
export async function setMarketingOptIn(userId: string, optIn: boolean): Promise<Profile> {
  const { data, error } = await supabase
    .from("profiles")
    .update({
      marketing_emails_opt_in: optIn,
      marketing_consent_at: new Date().toISOString(),
    })
    .eq("id", userId)
    .select("id, display_name, privacy_consent_at, marketing_emails_opt_in, marketing_consent_at")
    .single();
  if (error) throw new Error(error.message);
  return map(data);
}

/** Nome suggerito dal provider social (Google/Apple), se disponibile. */
export function providerName(meta: Record<string, unknown> | undefined): string {
  const candidates = ["full_name", "name", "given_name"];
  for (const key of candidates) {
    const value = meta?.[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return "";
}
