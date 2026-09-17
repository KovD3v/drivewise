import { afterEach, expect, test, vi } from 'vitest';
import { mockVehicleDetails } from '@/api/mockData';
import { createGuidedDecision, addGuidedDecisionTurn } from '@/api/drivewise';
import { fromApiVehicle, getVehicleById, getVehiclesByType } from './vehicleService';
import { rankVehicles, toPreview } from '@/lib/decision-engine';
import { saveAnalysis, listSavedAnalyses } from '@/lib/saved-analyses';
import { signInMock } from '@/lib/mock-account';

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); localStorage.clear(); });

test('new vehicle screens reuse canonical API ids, price and specs', async () => {
  const detail = mockVehicleDetails[0];
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => detail }));
  expect(await getVehicleById(detail.id)).toEqual(fromApiVehicle(detail));
  expect(fetch).toHaveBeenCalledWith(`http://127.0.0.1:8000/vehicles/${detail.id}`);
  expect(fromApiVehicle(detail).dimensions?.boot_liters).toBe(detail.specs[0].cargo_volume_liters);
});

test('existing service failures do not silently become ZIP data', async () => {
  vi.stubEnv('VITE_USE_MOCK_API', 'false');
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({ detail: 'Unavailable' }) }));
  await expect(getVehiclesByType('car')).rejects.toThrow('Unavailable');
  await expect(createGuidedDecision('Auto per la città')).rejects.toThrow('Unavailable');
});

test('guided turns preserve the backend decision id and expected version', async () => {
  const response = { decisionId: 'decision-123', profileVersion: 2 };
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => response }));
  expect(await addGuidedDecisionTurn('decision-123', '15000', 1)).toEqual(response);
  expect(fetch).toHaveBeenCalledWith('http://127.0.0.1:8000/guided-decisions/decision-123/turns', expect.objectContaining({
    method: 'POST', body: JSON.stringify({ message: '15000', expectedProfileVersion: 1 }),
  }));
});

test('report preserves backend score, reasons and uncertainty without local rescoring', async () => {
  const vehicle = mockVehicleDetails[0];
  const response = { previewRanking: { groups: [{ items: [{ vehicle, selected_spec: vehicle.specs[0], score: 73.25,
    positive_factors: [{ message: 'Backend reason' }], tradeoffs: [{ message: 'Backend tradeoff' }] }] }], assumptions: ['Assumption'] },
    warnings: ['Warning'], garageCompatibility: [{ vehicleId: vehicle.id, specId: vehicle.specs[0].id, message: 'Insufficient garage measurements' }] };
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => response }));
  const result = await rankVehicles({ vehicleType: 'car', decisionId: 'decision-123' });
  expect(result[0].score).toBe(73.25);
  expect(result[0].why).toEqual(['Backend reason']);
  expect(result[0].tradeoffs).toEqual(['Backend tradeoff', 'Assumption', 'Warning', 'Insufficient garage measurements']);
});

test('missing two-wheel and account services are explicit browser mocks with no network', async () => {
  vi.stubGlobal('fetch', vi.fn());
  const ranking = await rankVehicles({ vehicleType: 'motorcycle' });
  expect(ranking.length).toBeGreaterThan(0);
  expect(ranking.every(r => r.vehicle.mock)).toBe(true);
  signInMock();
  await saveAnalysis({ vehicleId: ranking[0].vehicle.id, brand: 'Demo', model: 'Demo', score: 85, confidence: 50, tags: [], profile: { vehicleType: 'motorcycle' } }, 'demo-local');
  expect(await listSavedAnalyses()).toHaveLength(1);
  expect(fetch).not.toHaveBeenCalled();
});

test('ranking preserves complete-first backend order, ties and assessment status', async () => {
  const vehicle = mockVehicleDetails[0];
  const item = (id: string, score: number, decision_status: string) => ({
    vehicle: { ...vehicle, id }, selected_spec: vehicle.specs[0], score, decision_status,
    positive_factors: [], tradeoffs: [],
  });
  const response = {
    previewRanking: { groups: [{ items: [item('complete', 70, 'complete'), item('tie', 70, 'complete'), item('provisional', 90, 'insufficient_data')] }], assumptions: [] },
    warnings: [], garageCompatibility: [],
  };
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => response }));
  const ranking = await rankVehicles({ vehicleType: 'car', decisionId: 'decision-123' });
  expect(ranking.map(item => item.vehicle.id)).toEqual(['complete', 'tie', 'provisional']);
  expect(ranking[2].decisionStatus).toBe('insufficient_data');
  expect(toPreview(ranking[2]).decisionStatus).toBe('insufficient_data');
});
