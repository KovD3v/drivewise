import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { CustomizableFeatureGrid } from './CustomizableFeatureGrid'

vi.mock('@/components/transition/AppTransitionLink', () => ({ AppTransitionLink: ({ children }: { children: React.ReactNode }) => <a>{children}</a> }))
beforeEach(() => { vi.stubGlobal('IntersectionObserver', class { observe() {} unobserve() {} disconnect() {} takeRecords() { return [] } }) })
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear() })

const savedOrder = () => (JSON.parse(localStorage.getItem('drivewise_me_layout_v1')!) as { order: string[] }).order

test('dashboard cards reorder from the keyboard with move buttons, disabled at the section ends', async () => {
  render(<CustomizableFeatureGrid />)
  fireEvent.click(screen.getByRole('button', { name: 'Personalizza' }))

  // The first card of a section cannot move earlier, the last cannot move later.
  expect(screen.getByRole('button', { name: 'Sposta prima I miei veicoli' })).toHaveAttribute('aria-disabled', 'true')
  expect(screen.getByRole('button', { name: 'Sposta dopo Confronti salvati' })).toHaveAttribute('aria-disabled', 'true')
  fireEvent.click(screen.getByRole('button', { name: 'Sposta dopo Confronti salvati' }))
  expect(localStorage.getItem('drivewise_me_layout_v1')).toBeNull()

  const later = screen.getByRole('button', { name: 'Sposta dopo I miei veicoli' })
  later.focus()
  fireEvent.click(later)
  expect(savedOrder().slice(0, 2)).toEqual(['decision-history', 'garage'])
  // The moved card's button keeps the keyboard focus, so the user can press it again.
  await waitFor(() => expect(later).toHaveFocus())

  fireEvent.click(screen.getByRole('button', { name: 'Sposta prima I miei veicoli' }))
  expect(savedOrder().slice(0, 2)).toEqual(['garage', 'decision-history'])
})
