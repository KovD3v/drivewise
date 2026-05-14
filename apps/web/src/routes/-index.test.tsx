import { screen } from '@testing-library/react'

import { Home } from '../views/Home'
import { renderWithRouter } from '../test/renderWithRouter'

test('renders the Drivewise MVP heading', () => {
  renderWithRouter(<Home />)

  expect(screen.getByRole('heading', { name: 'Drivewise MVP' })).toBeVisible()
})
