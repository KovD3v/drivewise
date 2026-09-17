import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { GuidedCarFlow } from './GuidedCarFlow';
import { createGuidedDecision, addGuidedDecisionTurn } from '@/api/drivewise';

vi.mock('@tanstack/react-router', () => ({ useNavigate: () => vi.fn(), Link: ({ children }: { children: React.ReactNode }) => <a>{children}</a> }));
vi.mock('@/api/drivewise', () => ({ createGuidedDecision: vi.fn(), addGuidedDecisionTurn: vi.fn(), fetchGuidedDecision: vi.fn() }));
beforeEach(() => { vi.spyOn(window, 'scrollTo').mockImplementation(() => {}); });
afterEach(() => { cleanup(); vi.resetAllMocks(); vi.restoreAllMocks(); localStorage.clear(); });

const response = {
  decisionId: 'decision-123', profileVersion: 1, profileCompletion: 0.42, decisionConfidence: 0.61,
  decisionProfile: { category: { value: 'hatchback' } }, missingInformation: [],
  nextQuestion: { id: 'budget_eur', type: 'number' as const, label: 'Budget massimo?', reason: 'Serve per il confronto.', constraints: { minimum: 1000, maximum: null, unit: 'EUR', options: [] } },
  previewRanking: { status: 'blocked' as const, groups: [], assumptions: [], blockingReasons: [] },
  garageCompatibility: [], warnings: [], contractVersion: 'guided-decision-v1' as const, status: 'active' as const, message: '',
};

test('reference category intake preserves selected category, retry and versioned backend turns', async () => {
  vi.mocked(createGuidedDecision).mockRejectedValueOnce(new Error('Servizio non disponibile')).mockResolvedValueOnce(response);
  vi.mocked(addGuidedDecisionTurn).mockResolvedValue({ ...response, profileVersion: 2 });
  render(<GuidedCarFlow initialQuery="Auto per la città" />);
  expect(createGuidedDecision).not.toHaveBeenCalled();
  expect(screen.queryByPlaceholderText('Descrivi liberamente cosa cerchi')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Hatchback' }));
  await screen.findByPlaceholderText('Descrivi liberamente cosa cerchi');
  fireEvent.click(screen.getByRole('button', { name: 'Invia risposta' }));
  await screen.findByRole('alert');
  expect(createGuidedDecision).toHaveBeenCalledWith('Cerco una compatta. Auto per la città');
  fireEvent.click(screen.getByRole('button', { name: 'Riprova' }));
  await screen.findByLabelText('Budget massimo?');
  expect(createGuidedDecision).toHaveBeenCalledTimes(2);
  fireEvent.change(screen.getByLabelText('Budget massimo?'), { target: { value: '18000' } });
  fireEvent.click(screen.getByRole('button', { name: 'Conferma' }));
  await waitFor(() => expect(addGuidedDecisionTurn).toHaveBeenCalledWith('decision-123', '18000', 1));
});

test('unknown category adds no invented category and oversized requests never reach the API', async () => {
  render(<GuidedCarFlow initialQuery="" />);
  fireEvent.click(screen.getByRole('button', { name: 'Non lo so ancora' }));
  const input = await screen.findByPlaceholderText('Descrivi liberamente cosa cerchi');
  fireEvent.change(input, { target: { value: 'a'.repeat(2001) } });
  fireEvent.click(screen.getByRole('button', { name: 'Invia risposta' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('2000');
  expect(createGuidedDecision).not.toHaveBeenCalled();
  vi.mocked(createGuidedDecision).mockResolvedValueOnce(response);
  fireEvent.change(input, { target: { value: 'Auto per la città' } });
  fireEvent.click(screen.getByRole('button', { name: 'Invia risposta' }));
  await waitFor(() => expect(createGuidedDecision).toHaveBeenCalledWith('Auto per la città'));
});

test.each([
  ['parking', 'single_select', 'Nessun posto auto'],
  ['constraint_modes', 'multi_select', 'Nessun vincolo obbligatorio'],
] as const)('submits canonical none for %s without using its display label', async (id, type, label) => {
  const next = { ...response, nextQuestion: { ...response.nextQuestion, id, type, constraints: { ...response.nextQuestion.constraints, options: ['none'] } } };
  vi.mocked(createGuidedDecision).mockResolvedValue(next);
  vi.mocked(addGuidedDecisionTurn).mockResolvedValue({ ...response, profileVersion: 2 });
  render(<GuidedCarFlow initialQuery="Auto per la città" />);
  fireEvent.click(screen.getByRole('button', { name: 'Non lo so ancora' }));
  await screen.findByPlaceholderText('Descrivi liberamente cosa cerchi');
  fireEvent.click(screen.getByRole('button', { name: 'Invia risposta' }));
  fireEvent.click(await screen.findByRole('button', { name: label }));
  if (type === 'multi_select') fireEvent.click(screen.getByRole('button', { name: 'Conferma selezione' }));
  await waitFor(() => expect(addGuidedDecisionTurn).toHaveBeenCalledWith('decision-123', 'none', 1));
  expect(await screen.findByText(label)).toBeInTheDocument();
});
