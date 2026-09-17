import { useSyncExternalStore } from "react";

export type TransitionOrigin = { x: number; y: number } | null;

type State = { active: boolean; origin: TransitionOrigin; id: number; steps?: string[] };

type TransitionStore = {
  state: State;
  listeners: Set<() => void>;
};

const STORE_KEY = "__drivewiseAppTransitionStore";

function getStore(): TransitionStore {
  const root = globalThis as typeof globalThis & {
    [STORE_KEY]?: TransitionStore;
  };
  root[STORE_KEY] ??= {
    state: { active: false, origin: null, id: 0 },
    listeners: new Set(),
  };
  return root[STORE_KEY];
}

function emit() {
  getStore().listeners.forEach((l) => l());
}

/** Avvia l'overlay di transizione. Non blocca né ritarda la navigazione. */
export function startAppTransition(origin: TransitionOrigin, steps?: string[]) {
  const store = getStore();
  store.state = { active: true, origin, id: store.state.id + 1, ...(steps ? { steps } : {}) };
  emit();
}

export function endAppTransition() {
  const store = getStore();
  if (!store.state.active) return;
  store.state = { ...store.state, active: false };
  emit();
}

function subscribe(l: () => void) {
  const listeners = getStore().listeners;
  listeners.add(l);
  return () => listeners.delete(l);
}

const server: State = { active: false, origin: null, id: 0 };

export function useAppTransition() {
  return useSyncExternalStore(
    subscribe,
    () => getStore().state,
    () => server,
  );
}
