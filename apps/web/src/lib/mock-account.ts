// ponytail: browser-only demo account; replace with real auth when the backend supports accounts.
export type MockUser = { id: string; user_metadata: Record<string, unknown> };
const KEY = 'drivewise_mock_account';
export function readMockUser(): MockUser | null {
  try { return JSON.parse(localStorage.getItem(KEY) ?? 'null'); } catch { return null; }
}
export function signInMock() {
  const user: MockUser = { id: 'demo-local', user_metadata: {} };
  localStorage.setItem(KEY, JSON.stringify(user));
  window.dispatchEvent(new Event(KEY));
}
export const MOCK_ACCOUNT_EVENT = KEY;
