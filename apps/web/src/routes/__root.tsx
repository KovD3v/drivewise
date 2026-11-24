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
import { AppHeader } from '@/components/app/AppHeader'

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
  return (
    <RootDocument>
      <Outlet />
      <PageTransition />
    </RootDocument>
  )
}

export function NotFoundPage() {
  return (
    <div className="min-h-screen bg-background">
      <AppHeader label="Pagina non trovata" />
      <main className="mx-auto w-full max-w-[46rem] px-6 py-24 text-center sm:px-8">
        <h1 className="font-heading text-[2rem] font-extrabold tracking-[-0.03em]">Pagina non trovata</h1>
        <p className="mt-4 text-[0.95rem] text-muted-foreground">
          La pagina richiesta non esiste o è stata spostata.
        </p>
        <nav className="mt-8 flex flex-wrap justify-center gap-3" aria-label="Navigazione 404">
          <Link
            to="/"
            className="inline-flex h-12 items-center rounded-full bg-primary px-7 text-[0.95rem] font-medium text-primary-foreground transition-colors hover:bg-primary-hover"
          >
            Home
          </Link>
          <Link
            to="/app/start"
            className="inline-flex h-12 items-center rounded-full border border-border bg-card px-7 text-[0.95rem]"
          >
            Scelta Guidata
          </Link>
        </nav>
      </main>
    </div>
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
