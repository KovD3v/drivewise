import { expect, test } from 'vitest'
import fixture from '@/test/fixtures/guided-decision.synthetic.json'
import type { GuidedDecisionResponse } from '@/api/drivewise'
import { guidedRanking, guidedRankingGroups, topRankingGroup } from './decision-engine'

const decision = fixture as unknown as GuidedDecisionResponse
type Item = GuidedDecisionResponse['previewRanking']['groups'][number]['items'][number]
const template = decision.previewRanking.groups[0]!.items[0]!

function item(vehicleId: string, score: number, status: Item['decision_status'] = 'complete', specId = `${vehicleId}-spec`): Item {
  return { ...template, vehicle: { ...template.vehicle, id: vehicleId }, selected_spec: { ...template.selected_spec, id: specId }, score, decision_status: status }
}
function withGroups(groups: { condition: 'new' | 'used'; items: Item[] }[]): GuidedDecisionResponse {
  return { ...decision, previewRanking: { ...decision.previewRanking, groups }, garageCompatibility: [] }
}

test('a used offer that outranks the new winner is never displaced by it', () => {
  const response = withGroups([
    { condition: 'new', items: [item('new-car', 70)] },
    { condition: 'used', items: [item('used-car', 85)] },
  ])
  const groups = guidedRankingGroups(response)
  expect(groups.map((g) => [g.condition, g.items.map((i) => i.vehicle.id)])).toEqual([['new', ['new-car']], ['used', ['used-car']]])
  expect(topRankingGroup(groups)?.condition).toBe('used')
  expect(guidedRanking(response).map((i) => i.vehicle.id)).toEqual(['used-car', 'new-car'])
})

test('the same version ranked new and used stays in both groups and keeps its better entry in the flat list', () => {
  const response = withGroups([
    { condition: 'new', items: [item('same-car', 70)] },
    { condition: 'used', items: [item('same-car', 85)] },
  ])
  const groups = guidedRankingGroups(response)
  expect(groups.map((g) => g.items[0]!.score)).toEqual([70, 85])
  const flat = guidedRanking(response)
  expect(flat).toHaveLength(1)
  expect(flat[0]).toMatchObject({ score: 85, condition: 'used' })
})

test('a complete assessment outranks a higher provisional score, and an empty group disappears', () => {
  const response = withGroups([
    { condition: 'new', items: [item('complete-car', 70)] },
    { condition: 'used', items: [item('provisional-car', 90, 'insufficient_data')] },
  ])
  expect(topRankingGroup(guidedRankingGroups(response))?.condition).toBe('new')
  expect(guidedRankingGroups(withGroups([{ condition: 'new', items: [] }, { condition: 'used', items: [item('only', 60)] }])).map((g) => g.condition)).toEqual(['used'])
})

test('one group deduplicates by vehicle and version, not by vehicle alone', () => {
  const response = withGroups([{ condition: 'used', items: [item('car', 80, 'complete', 'spec-a'), item('car', 79, 'complete', 'spec-a'), item('car', 75, 'complete', 'spec-b')] }])
  expect(guidedRankingGroups(response)[0]!.items.map((i) => [i.specId, i.score])).toEqual([['spec-a', 80], ['spec-b', 75]])
})
