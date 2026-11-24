import { expect, test } from 'vitest'

import { formatListEur } from './source-facts'

test('shows cents only when a list price has them', () => {
  expect(formatListEur(12200.01).replace(/\s/g, ' ')).toBe('12.200,01 €')
  expect(formatListEur(12200.5).replace(/\s/g, ' ')).toBe('12.200,50 €')
  expect(formatListEur(30500).replace(/\s/g, ' ')).toBe('30.500 €')
})
