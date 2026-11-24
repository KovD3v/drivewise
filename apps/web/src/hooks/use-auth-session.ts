import { useEffect, useState } from 'react';
import { readMockUser, MOCK_ACCOUNT_EVENT, type MockUser } from '@/lib/mock-account';
export function useAuthSession() {
  const [user, setUser] = useState<MockUser | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const update = () => { setUser(readMockUser()); setReady(true); };
    update();
    window.addEventListener(MOCK_ACCOUNT_EVENT, update);
    window.addEventListener('storage', update);
    return () => { window.removeEventListener(MOCK_ACCOUNT_EVENT, update); window.removeEventListener('storage', update); };
  }, []);
  return { user, session: user ? { user } : null, ready };
}
