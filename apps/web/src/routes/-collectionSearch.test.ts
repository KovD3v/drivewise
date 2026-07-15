import { expect, test } from 'vitest'

import {
  validateDocumentSearch,
  validateListingSearch,
  validateVehicleSearch,
} from './-collectionSearch'

test('normalizes supported vehicle search values and drops unknown input', () => {
  expect(
    validateVehicleSearch({
      make: '  Fiat ',
      market: 'it',
      max_price_eur: '25000',
      ignored: 'value',
    }),
  ).toEqual({
    make: 'Fiat',
    market: 'IT',
    max_price_eur: 25000,
  })
})

test('rejects invalid listing numeric filters', () => {
  expect(
    validateListingSearch({
      model: 'Panda',
      max_price_eur: '-1',
      max_mileage: '12.5',
    }),
  ).toEqual({ model: 'Panda' })
})

test('bounds document limits and preserves valid queries', () => {
  expect(validateDocumentSearch({ q: ' Fiat Panda ', limit: '20' })).toEqual({
    q: 'Fiat Panda',
    limit: 20,
  })
  expect(validateDocumentSearch({ limit: '101' })).toEqual({})
})
