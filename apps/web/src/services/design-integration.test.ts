import { afterEach, expect, test, vi } from 'vitest';
import carDetail from '@/test/fixtures/car-detail.synthetic.json';
import type { VehicleDetail } from '@/api/drivewise';

const sampleDetail = carDetail as VehicleDetail;
import { createGuidedDecision, addGuidedDecisionTurn } from '@/api/drivewise';
import { fromApiVehicle, getVehicleById, getVehiclesByType } from './vehicleService';
import { loadDecisionReport, rankVehicles, toPreview } from '@/lib/decision-engine';
import scooterDetail from '@/test/fixtures/scooter-detail.synthetic.json';
import { saveAnalysis, listSavedAnalyses } from '@/lib/saved-analyses';
import { signInMock } from '@/lib/mock-account';

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); localStorage.clear(); });

test('new vehicle screens reuse canonical API ids, price and specs', async () => {
  const detail = sampleDetail;
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => detail }));
  expect(await getVehicleById(detail.id)).toEqual(fromApiVehicle(detail));
  expect(fetch).toHaveBeenCalledWith(`http://127.0.0.1:8000/vehicles/${detail.id}`);
  expect(fromApiVehicle(detail).dimensions?.boot_liters).toBe(detail.specs[0].cargo_volume_liters);
});

test('existing service failures do not silently become ZIP data', async () => {
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
  const vehicle = sampleDetail;
  const response = { previewRanking: { groups: [{ items: [{ vehicle, selected_spec: vehicle.specs[0], score: 73.25,
    positive_factors: [{ message: 'Backend reason' }], tradeoffs: [{ message: 'Backend tradeoff' }] }] }], assumptions: ['Assumption'] },
    warnings: ['Warning'], garageCompatibility: [{ vehicleId: vehicle.id, specId: vehicle.specs[0].id, message: 'Insufficient garage measurements' }] };
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => response }));
  const result = await rankVehicles({ vehicleType: 'car', decisionId: 'decision-123' });
  expect(result[0].score).toBe(73.25);
  expect(result[0].why).toEqual(['Backend reason']);
  expect(result[0].tradeoffs).toEqual(['Backend tradeoff', 'Assumption', 'Warning', 'Insufficient garage measurements']);
});

test('two-wheelers are never ranked and need no guided decision call', async () => {
  vi.stubGlobal('fetch', vi.fn());
  expect(await loadDecisionReport({ vehicleType: 'motorcycle' })).toEqual({ ranking: [], confidence: null });
  expect(await loadDecisionReport({ vehicleType: 'car' })).toEqual({ ranking: [], confidence: null });
  expect(fetch).not.toHaveBeenCalled();
});

test('the report confidence is the one the Guided Decision API returns', async () => {
  const response = { decisionConfidence: 0.634, previewRanking: { groups: [], assumptions: [] }, warnings: [], garageCompatibility: [] };
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => response }));
  expect((await loadDecisionReport({ vehicleType: 'car', decisionId: 'decision-123' })).confidence).toBe(63);
});

test('a two-wheel detail keeps its catalogue facts, list price and credits, with no score', () => {
  const vehicle = fromApiVehicle(scooterDetail as VehicleDetail);
  expect(vehicle.vehicle_type).toBe('scooter');
  expect(vehicle.two_wheel).not.toBeNull();
  expect(vehicle).not.toHaveProperty('score');
  expect(vehicle.credits.map(c => c.name)).toContain(scooterDetail.specs[0].list_price?.source_name);
});

test('the catalogue keeps only the requested type, dropping untyped legacy rows', async () => {
  const rows = [{ ...scooterDetail, specs: undefined }, { ...sampleDetail, id: 'legacy', vehicle_type: null }];
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => rows }));
  expect((await getVehiclesByType('scooter')).map(v => v.id)).toEqual([scooterDetail.id]);
  expect(fetch).toHaveBeenCalledWith('http://127.0.0.1:8000/vehicles?vehicle_type=scooter&limit=100&offset=0');
});

test('saved analyses stay a local browser mock with no network', async () => {
  vi.stubGlobal('fetch', vi.fn());
  signInMock();
  await saveAnalysis({ vehicleId: sampleDetail.id, brand: 'Demo', model: 'Demo', score: 85, confidence: 50, tags: [], profile: { vehicleType: 'car' } }, 'demo-local');
  expect(await listSavedAnalyses()).toHaveLength(1);
  expect(fetch).not.toHaveBeenCalled();
});

test('ranking preserves complete-first backend order, ties and assessment status', async () => {
  const vehicle = sampleDetail;
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

test('a ranked version keeps the fuel the catalogue stores on the version', () => {
  const vehicle = fromApiVehicle({ ...sampleDetail, fuel_type: null, specs: [{ ...sampleDetail.specs[0], fuel_type: 'petrol' }] });
  expect(vehicle.powertrain.fuel).toBe('petrol');
});
