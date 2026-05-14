import { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { RouterContextProvider } from '@tanstack/react-router'

import { getRouter } from '../router'

export function renderWithRouter(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) {
  return render(
    <RouterContextProvider router={getRouter()}>{ui}</RouterContextProvider>,
    options,
  )
}
