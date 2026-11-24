import { afterEach, expect, test, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { PrioritySelector } from './PrioritySelector'

afterEach(cleanup)

const pressed = () => screen.getAllByRole('button', { pressed: true }).map((b) => b.textContent?.replace(/\d°/, ''))

test('priorities stay a top 3 by default', () => {
  const onConfirm = vi.fn()
  render(<PrioritySelector options={['A', 'B', 'C', 'D']} onConfirm={onConfirm} />)
  for (const o of ['A', 'B', 'C', 'D']) fireEvent.click(screen.getByRole('button', { name: o }))
  expect(pressed()).toEqual(['A', 'B', 'C'])
  expect(screen.getByText('3/3 selezionate')).toBeInTheDocument()
})

test('constraint modes may all apply, and "none" excludes every other option', () => {
  const onConfirm = vi.fn()
  const options = ['Budget', 'Carrozzeria', 'Alimentazione', 'Cambio', 'Nessun vincolo obbligatorio']
  render(<PrioritySelector options={options} max={5} exclusive={['Nessun vincolo obbligatorio']} ranked={false} onConfirm={onConfirm} />)
  for (const o of options.slice(0, 4)) fireEvent.click(screen.getByRole('button', { name: o }))
  expect(pressed()).toEqual(options.slice(0, 4))

  fireEvent.click(screen.getByRole('button', { name: 'Nessun vincolo obbligatorio' }))
  expect(pressed()).toEqual(['Nessun vincolo obbligatorio'])

  fireEvent.click(screen.getByRole('button', { name: 'Cambio' }))
  expect(pressed()).toEqual(['Cambio'])
  fireEvent.click(screen.getByRole('button', { name: 'Conferma selezione' }))
  expect(onConfirm).toHaveBeenCalledWith(['Cambio'])
})
