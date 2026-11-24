import type { ReactNode } from 'react'
import {
  createRootRoute,
  HeadContent,
  Link,
  Outlet,
  Scripts,
  useRouterState,
} from '@tanstack/react-router'

import { useEffect } from 'react'
import { PageTransition } from '@/components/transition/PageTransition'
import { CONTACT_SOURCE_KEY } from '@/lib/contact-intelligence'
import legacyStyles from '../legacy.css?url'

import appStyles from '../styles.css?url'


export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      { title: 'DriveWise' },
      { name: 'description', content: 'Analisi decisionale per la tua prossima scelta di mobilità.' },
      { name: 'author', content: 'DriveWise' },
      { name: 'theme-color', content: '#F4FAF7' },
      { property: 'og:title', content: 'DriveWise' },
      { property: 'og:description', content: 'Analisi decisionale per la tua prossima scelta di mobilità.' },
      { property: 'og:type', content: 'website' },
      { name: 'twitter:card', content: 'summary_large_image' },
      { name: 'twitter:title', content: 'DriveWise' },
      { name: 'twitter:description', content: 'Analisi decisionale per la tua prossima scelta di mobilità.' },
    ],
    links: [
      ...(legacyStyles ? [{ rel: 'stylesheet', href: legacyStyles }] : []),
      { rel: 'icon', href: '/favicon.png?v=3', type: 'image/png' },
      ...(appStyles ? [{ rel: 'stylesheet', href: appStyles }] : []),
      { rel: 'apple-touch-icon', sizes: '180x180', href: '/apple-touch-icon.png' },
    ],
  }),
  component: RootComponent,
  notFoundComponent: NotFoundPage,
})

function RootComponent() {
  const path = useRouterState({ select: s => s.location.pathname });
  useEffect(() => {
    if (path === '/contact') return
    try { sessionStorage.setItem(CONTACT_SOURCE_KEY, path) } catch { /* storage unavailable */ }
  }, [path])
  const legacy = !['/', '/contact', '/privacy', '/terms'].includes(path) && !path.startsWith('/app/');
  return (
    <RootDocument>
      <div className={legacy ? "legacy-ui" : undefined}><Outlet /></div>
      <PageTransition />
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
