import { screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import {
  mockDocumentDetails,
  mockListings,
  mockVehicleDetails,
} from '../api/mockData'
import { renderWithRouter } from '../test/renderWithRouter'
import { DocumentDetailPage } from './DocumentDetail'
import { ListingDetailPage } from './ListingDetail'
import { VehicleDetailPage } from './VehicleDetail'

test('renders vehicle detail loader data', () => {
  renderWithRouter(<VehicleDetailPage vehicle={mockVehicleDetails[0]} />)

  expect(screen.getByRole('heading', { name: 'Fiat Panda' })).toBeVisible()
  expect(screen.getByText('1.0 FireFly Hybrid')).toBeVisible()
  expect(screen.getByText('70 CV')).toBeVisible()
})

test('renders listing detail loader data and its vehicle link', () => {
  renderWithRouter(<ListingDetailPage listing={mockListings[0]} />)

  expect(
    screen.getByRole('heading', { name: 'Fiat Panda 1.0 FireFly Hybrid' }),
  ).toBeVisible()
  expect(screen.getByText('Piemonte')).toBeVisible()
  expect(screen.getByRole('link', { name: 'Dettaglio veicolo' })).toHaveAttribute(
    'href',
    `/vehicles/${mockListings[0].vehicle.id}`,
  )
})

test('renders document detail loader data without embedding metadata', () => {
  const document = {
    ...mockDocumentDetails[0],
    metadata: {
      ...mockDocumentDetails[0].metadata,
      embedding: [0.1, 0.2],
      nested: { embedding_model: 'private-model', visible: true },
    },
  }
  renderWithRouter(<DocumentDetailPage document={document} />)

  expect(
    screen.getByRole('heading', { name: 'Synthetic profile: Fiat Panda' }),
  ).toBeVisible()
  expect(screen.getByText(/compact Italian city car/)).toBeVisible()
  expect(screen.getByText(/"visible": true/)).toBeVisible()
  expect(screen.queryByText(/private-model/)).not.toBeInTheDocument()
  expect(screen.queryByText(/"embedding"/)).not.toBeInTheDocument()
})
