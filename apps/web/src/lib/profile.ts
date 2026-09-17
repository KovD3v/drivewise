// ponytail: local profile mock until an account API exists.
export type Profile = {
  id: string;
  displayName: string | null;
  privacyConsentAt: string | null;
  marketingEmailsOptIn: boolean;
  marketingConsentAt: string | null;
};

export async function getMyProfile(userId: string): Promise<Profile> {
  const raw = localStorage.getItem(`drivewise_mock_profile_${userId}`);
  return raw ? JSON.parse(raw) : { id: userId, displayName: null, privacyConsentAt: null, marketingEmailsOptIn: false, marketingConsentAt: null };
}
async function update(userId: string, patch: Partial<Profile>): Promise<Profile> {
  const profile = { ...await getMyProfile(userId), ...patch };
  localStorage.setItem(`drivewise_mock_profile_${userId}`, JSON.stringify(profile));
  return profile;
}
export async function completeOnboarding(userId: string, displayName: string) {
  return update(userId, { displayName: displayName.trim(), privacyConsentAt: new Date().toISOString() });
}
export async function setMarketingOptIn(userId: string, optIn: boolean) {
  return update(userId, { marketingEmailsOptIn: optIn, marketingConsentAt: new Date().toISOString() });
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
