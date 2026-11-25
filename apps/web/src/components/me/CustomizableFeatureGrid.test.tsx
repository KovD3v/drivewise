import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { CustomizableFeatureGrid } from './CustomizableFeatureGrid'

vi.mock('@/components/transition/AppTransitionLink', () => ({ AppTransitionLink: ({ children }: { children: React.ReactNode }) => <a>{children}</a> }))
beforeEach(() => { vi.stubGlobal('IntersectionObserver', class { observe() {} unobserve() {} disconnect() {} takeRecords() { return [] } }) })
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear() })

const savedOrder = () => (JSON.parse(localStorage.getItem('drivewise_me_layout_v1')!) as { order: string[] }).order

test('dashboard cards reorder from the keyboard with move buttons, disabled at the section ends', () => {
  render(<CustomizableFeatureGrid />)
  fireEvent.click(screen.getByRole('button', { name: 'Personalizza' }))

  // The first card of a section cannot move earlier, the last cannot move later.
  expect(screen.getByRole('button', { name: 'Sposta prima I miei veicoli' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Sposta dopo Confronti salvati' })).toBeDisabled()

  fireEvent.click(screen.getByRole('button', { name: 'Sposta dopo I miei veicoli' }))
  expect(savedOrder().slice(0, 2)).toEqual(['decision-history', 'garage'])

  fireEvent.click(screen.getByRole('button', { name: 'Sposta prima I miei veicoli' }))
  expect(savedOrder().slice(0, 2)).toEqual(['garage', 'decision-history'])
})
