import { render, screen } from '@testing-library/react'
import { RouterContextProvider } from '@tanstack/react-router'

import { getRouter } from '../router'
import { Route } from './__root'

test('configures a root not found page with navigation links', () => {
  const NotFoundComponent = Route.options.notFoundComponent

  expect(NotFoundComponent).toBeDefined()

  if (!NotFoundComponent) {
    throw new Error('Root route does not configure notFoundComponent')
  }

  render(
    <RouterContextProvider router={getRouter()}>
      <NotFoundComponent
        data={undefined}
        isNotFound
        routeId="__root__"
      />
    </RouterContextProvider>,
  )

  expect(
    screen.getByRole('heading', { name: 'Pagina non trovata' }),
  ).toBeVisible()
  expect(
    screen.getByText(/non esiste o e stata spostata/i),
  ).toBeVisible()
  expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/')
  expect(screen.getByRole('link', { name: 'Veicoli' })).toHaveAttribute(
    'href',
    '/vehicles',
  )
  expect(screen.getByRole('link', { name: 'Annunci' })).toHaveAttribute(
    'href',
    '/listings',
  )
  expect(screen.getByRole('link', { name: 'Documenti' })).toHaveAttribute(
    'href',
    '/documents',
  )
  expect(screen.getByRole('link', { name: 'Search' })).toHaveAttribute(
    'href',
    '/search',
  )
  expect(screen.getByRole('link', { name: 'Advisor' })).toHaveAttribute(
    'href',
    '/advisor',
  )
})
