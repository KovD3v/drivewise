import type { ReactNode } from 'react'
import {
  createRootRoute,
  HeadContent,
  Link,
  Outlet,
  Scripts,
} from '@tanstack/react-router'

import appStyles from '../styles.css?url'

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
          <Link className="secondary-link" to="/documents">
            Documenti
          </Link>
          <Link className="secondary-link" to="/advisor">
            Advisor
          </Link>
        </nav>
      </section>
    </main>
  )
}

function RootDocument({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
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
