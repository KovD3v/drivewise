import { Link } from '@tanstack/react-router'

export function Home() {
  return (
    <main className="app-shell">
      <section className="intro-panel" aria-labelledby="page-title">
        <p className="eyebrow">Vehicle purchase assistant</p>
        <h1 id="page-title">Drivewise MVP</h1>
        <p className="summary">
          A simple starting point for comparing vehicle data, pricing signals,
          and ownership context in later iterations.
        </p>
        <nav className="home-actions" aria-label="Drivewise sections">
          <Link className="primary-link" to="/vehicles">
            Veicoli
          </Link>
          <Link className="secondary-link" to="/listings">
            Annunci
          </Link>
          <Link className="secondary-link" to="/documents">
            Documenti
          </Link>
          <Link className="secondary-link" to="/search">
            Search
          </Link>
          <Link className="secondary-link" to="/advisor">
            Advisor
          </Link>
        </nav>
      </section>
    </main>
  )
}
