import { useRouter } from '@tanstack/react-router'

import { errorMessage } from '../views/viewUtils'

export function DataRoutePending() {
  return (
    <main className="browse-shell">
      <p className="status-message" role="status">
        Caricamento dati…
      </p>
    </main>
  )
}

export function DataRouteError({ error }: { error: unknown }) {
  const router = useRouter()

  return (
    <main className="browse-shell">
      <section className="route-error" role="alert">
        <p className="eyebrow">Errore di caricamento</p>
        <h1>Dati non disponibili</h1>
        <p className="error-message">
          {errorMessage(error, 'Impossibile caricare i dati')}
        </p>
        <button
          className="primary-button"
          onClick={() => void router.invalidate()}
          type="button"
        >
          Riprova
        </button>
      </section>
    </main>
  )
}
