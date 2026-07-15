import { fireEvent, render, screen } from '@testing-library/react'
import { RouterContextProvider } from '@tanstack/react-router'
import { expect, test, vi } from 'vitest'

import { getRouter } from '../router'
import { CollectionRouteError, CollectionRoutePending } from './-collectionStates'

test('renders a stable pending state for collection loaders', () => {
  render(<CollectionRoutePending />)

  expect(screen.getByRole('status')).toHaveTextContent(
    'Caricamento dati iniziali…',
  )
})

test('renders loader errors and retries through router invalidation', () => {
  const router = getRouter()
  const invalidate = vi.spyOn(router, 'invalidate').mockResolvedValue()

  render(
    <RouterContextProvider router={router}>
      <CollectionRouteError error={new Error('API unavailable')} />
    </RouterContextProvider>,
  )

  expect(screen.getByRole('alert')).toHaveTextContent('API unavailable')
  fireEvent.click(screen.getByRole('button', { name: 'Riprova' }))
  expect(invalidate).toHaveBeenCalledOnce()
})
