import type { ReactNode } from 'react'
import {
  createRootRoute,
  HeadContent,
  Link,
  Outlet,
  Scripts,
} from '@tanstack/react-router'

import appStyles from '../styles.css?url'

const faviconHref =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%231d4f48'/%3E%3Ctext x='32' y='41' text-anchor='middle' font-family='Arial,sans-serif' font-size='32' font-weight='700' fill='white'%3ED%3C/text%3E%3C/svg%3E"

export const Route = createRootRoute({
  head: () => ({
    meta: [
      {
        charSet: 'utf-8',
      },
      {
        name: 'viewport',
        content: 'width=device-width, initial-scale=1',
      },
      {
        title: 'Drivewise MVP',
      },
    ],
    links: [
      {
        rel: 'icon',
        href: faviconHref,
        type: 'image/svg+xml',
      },
      {
        rel: 'stylesheet',
        href: appStyles,
      },
    ],
  }),
  component: RootComponent,
  notFoundComponent: NotFoundPage,
})

function RootComponent() {
  return (
    <RootDocument>
      <Outlet />
    </RootDocument>
  )
}

export function NotFoundPage() {
  return (
    <main className="app-shell">
      <section className="intro-panel" aria-labelledby="not-found-title">
        <p className="eyebrow">Drivewise MVP</p>
        <h1 id="not-found-title">Pagina non trovata</h1>
        <p className="summary">
          La pagina richiesta non esiste o e stata spostata.
        </p>
        <nav className="home-actions" aria-label="Navigazione 404">
          <Link className="primary-link" to="/">
            Home
          </Link>
          <Link className="secondary-link" to="/vehicles">
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
          <Link className="secondary-link" to="/model-analysis">
            Analisi modello
          </Link>
        </nav>
      </section>
    </main>
  )
}

function RootDocument({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="it">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  )
}
