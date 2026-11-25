import { useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { EASE } from '@/lib/motion';
import { MobilePanel } from './MobilePanel';
import { useNavigate } from '@tanstack/react-router';
import { createGuidedDecision, addGuidedDecisionTurn, fetchGuidedDecision, isApiErrorCode, type GuidedDecisionResponse } from '@/api/drivewise';
import { guidedConfidence, guidedProfile, guidedRanking, toPreview } from '@/lib/decision-engine';
import { clearState, saveState } from '@/lib/decision-state';
import { AppHeader } from './AppHeader';
import { DecisionBar } from './DecisionBar';
import { DecisionMessage, TypingIndicator } from './DecisionMessage';
import { DecisionProfilePanel } from './DecisionProfilePanel';
import { StepStage } from './StepStage';
import { QuickChoice } from './QuickChoice';
import { PrioritySelector } from './PrioritySelector';
import { UserMessage } from './UserMessage';
import { ProgressNarrative } from './ProgressNarrative';

const categories = ['City Car', 'Crossover', 'Hatchback', 'Station Wagon', 'SUV', 'Utilitaria', 'Non lo so ancora'];
const categoryPrompt = 'Quale categoria stai considerando?';
const categoryHint = 'Le categorie disponibili nel catalogo DriveWise per questa scelta.';
const initialMissing = ['Categoria', 'Esigenza', 'Utilizzo', 'Priorità', 'Budget', 'Parcheggio', 'Passeggeri'];

const labels: Record<string, string> = {
  city: 'Città', highway: 'Autostrada', family: 'Famiglia', work: 'Lavoro', new_driver: 'Neopatentato',
  any: 'Nuova o usata, entrambe', new: 'Nuova', used: 'Usata', city_car: 'City car', small_hatchback: 'Berlina compatta',
  hatchback: 'Compatta', crossover: 'Crossover', suv: 'SUV', sedan: 'Berlina', wagon: 'Station wagon', mpv: 'Monovolume', van: 'Furgone',
  diesel: 'Diesel', electric: 'Elettrica', full_hybrid_petrol: 'Full hybrid', hybrid_petrol: 'Ibrida', mild_hybrid_petrol: 'Mild hybrid', petrol: 'Benzina', petrol_lpg: 'GPL',
  garage: 'Garage', covered_space: 'Posto auto coperto', outdoor_space: 'Posto auto scoperto', none: 'Nessun posto auto',
  price: 'Prezzo', efficiency_range: 'Autonomia', space: 'Spazio', running_cost: 'Costi di gestione',
  // constraint_modes options: which answers are hard constraints.
  budget: 'Budget massimo', body_style: 'Carrozzeria', fuel_type: 'Alimentazione', transmission: 'Cambio',
  budgetEur: 'Budget', annualKm: 'Km annui', primaryUse: 'Utilizzo', category: 'Categoria', condition: 'Condizione', preferredFuelType: 'Alimentazione', priorities: 'Priorità', parking: 'Parcheggio', vehicleType: 'Tipo veicolo', car: 'Auto',
  budget_eur: 'Budget', annual_km: 'Km annui', primary_use: 'Utilizzo', preferred_fuel_type: 'Alimentazione',
};

export { guidedProfile };

export function GuidedCarFlow({ initialQuery }: { initialQuery: string }) {
  const navigate = useNavigate();
  const [category, setCategory] = useState<string | null>(null);
  const [response, setResponse] = useState<GuidedDecisionResponse | null>(null);
  const [messages, setMessages] = useState<{ prompt: string; answer: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);
  const [error, setError] = useState('');
  // The API caps the turns of one session (409 max_turns_reached): the profile is kept, no answer is accepted.
  const [capped, setCapped] = useState(false);
  // The answer to resend and the profile version it answered: a newer version means a new question.
  const [retry, setRetry] = useState<{ message: string; version: number | null } | null>(null);
  const question = response?.nextQuestion;
  const choices = (question?.constraints?.options ?? []).map(value => ({
    value,
    label: value === 'none' && question?.id === 'constraint_modes'
      ? 'Nessun vincolo obbligatorio' : labels[value] ?? value,
  }));
  const optionValue = (label: string) => choices.find(choice => choice.label === label)?.value ?? label;
  // "none" excludes every other option; constraint modes may all apply at once, priorities stay a top 3.
  const exclusiveLabels = choices.filter(choice => choice.value === 'none').map(choice => choice.label);
  const maxPicks = question?.id === 'constraint_modes' ? Math.max(choices.length - exclusiveLabels.length, 1) : 3;
  const currentVersion = response?.profileVersion ?? null;
  const retryable = retry && retry.version === currentVersion ? retry : null;
  const ranking = response ? guidedRanking(response) : [];
  const completion = response ? Math.round(response.profileCompletion * 100) : Math.round((category === null ? 1 : 2) / 8 * 100);
  // Confidence belongs to the Guided Decision API: none is shown before its first answer.
  const confidence = response ? guidedConfidence(response) : null;
  const known = response ? Object.entries(response?.decisionProfile ?? {}).flatMap(([key, fact]) => {
    if (!fact || !('value' in fact)) return [];
    const value = fact.value;
    return [`${labels[key] ?? key}: ${Array.isArray(value) ? value.map(v => labels[v] ?? v).join(', ') : labels[String(value)] ?? String(value)}`];
  }) : ['Tipo veicolo: Auto', ...(category && category !== 'Non lo so ancora' ? [`Categoria: ${category}`] : [])];
  const persist = (next: GuidedDecisionResponse) => saveState({
    sessionId: next.decisionId, status: next.previewRanking.status === 'ready' ? 'ready' : 'collecting',
    currentStep: next.nextQuestion?.id ?? 'report', profile: guidedProfile(next), answers: {},
    profileCompletion: Math.round(next.profileCompletion * 100), decisionConfidence: guidedConfidence(next),
    rankingIds: [...new Set(guidedRanking(next).map(r => r.vehicle.id))], updatedAt: Date.now(),
  });
  const restart = () => {
    clearState(); setResponse(null); setMessages([]); setCategory(null);
    setError(''); setRetry(null); setCapped(false);
  };
  const submit = async (message: string) => {
    if (inFlight.current || capped || !message.trim()) return;
    const request = !response && category && category !== 'Non lo so ancora'
      ? `Cerco una ${category === 'Hatchback' ? 'compatta' : category}. ${message}` : message;
    if (request.length > 2000) { setError('Scrivi al massimo 2000 caratteri.'); return; }
    inFlight.current = true; setBusy(true); setError(''); setRetry({ message, version: response?.profileVersion ?? null });
    try {
      const next = response ? await addGuidedDecisionTurn(response.decisionId, message, response.profileVersion) : await createGuidedDecision(request);
      const answer = message.split(', ').map(value => choices.find(choice => choice.value === value)?.label ?? value).join(', ');
      setMessages(prev => [...prev, { prompt: question?.label ?? 'Raccontami cosa cerchi.', answer }]);
      setResponse(next); persist(next); setRetry(null);
    } catch (e) {
      if (isApiErrorCode(e, 'max_turns_reached')) { setCapped(true); setRetry(null); return; }
      setError(e instanceof Error ? e.message : 'Non riesco ad aggiornare il profilo. Riprova.');
      // Resync a possibly stale version before an explicit retry; never send a duplicate turn automatically.
      if (response) {
        try {
          const latest = await fetchGuidedDecision(response.decisionId);
          setResponse(latest); persist(latest);
          // The answer belonged to an older question: never resend it to the new one.
          if (latest.profileVersion !== response.profileVersion) setRetry(null);
        } catch { /* keep the last confirmed state */ }
      }
    } finally { inFlight.current = false; setBusy(false); }
  };
  return <div className="min-h-screen bg-background">
    <AppHeader label="Scelta Guidata" maxWidth="max-w-[86rem]" />
    <main className="mx-auto w-full max-w-[86rem] px-6 py-10 sm:px-8 lg:py-16">
      <div className="grid gap-10 lg:grid-cols-[7fr_3fr] lg:gap-14">
        <div className="min-w-0">
          <h1 className="font-heading text-[2.25rem] leading-[1.05] font-extrabold text-foreground sm:text-[3rem]">Trova il veicolo perfetto.</h1>
          <p className="mt-5 max-w-2xl text-[1.02rem] leading-relaxed text-muted-foreground">Le domande cambiano in base a ciò che stai cercando: ti chiediamo solo ciò che i dati reali dei veicoli permettono di valutare.</p>
          <div className="mt-9 space-y-8">
            <StepStage themeId="facts" active={false}><DecisionMessage><p>Cosa stai cercando?</p><p className="text-muted-foreground">Auto, moto o scooter: da qui cambia tutto il percorso.</p></DecisionMessage><div className="pl-[3.125rem]"><span className="inline-flex rounded-full border border-primary/35 bg-primary/10 px-4 py-2 text-[0.85rem]">Auto</span></div></StepStage>
            <ProgressNarrative completion={completion} remainingCount={response ? response.missingInformation.length : initialMissing.length - (category === null ? 0 : 1)} />
            <StepStage themeId="facts" active={category === null}>
              <DecisionMessage><p>{categoryPrompt}</p><p className="text-muted-foreground">{categoryHint}</p></DecisionMessage>
              <div className="pl-[3.125rem]">{category === null ? <QuickChoice options={categories} onSelect={setCategory} /> : <span className="inline-flex items-center rounded-full border border-primary/35 bg-primary/10 px-4 py-2 text-[0.85rem] text-foreground">{category}</span>}</div>
            </StepStage>
            {messages.map((m, i) => <StepStage key={i} themeId="facts" active={false}><DecisionMessage><p>{m.prompt}</p></DecisionMessage><UserMessage>{m.answer}</UserMessage></StepStage>)}
            {category !== null && !capped && (busy ? <DecisionMessage><TypingIndicator /></DecisionMessage> : <StepStage themeId={question?.id.includes('garage') ? 'garage' : question?.id === 'budget_eur' ? 'budget' : 'facts'} active>
              <DecisionMessage><p>{question?.label ?? (response ? 'Il tuo profilo è pronto.' : 'Raccontami cosa cerchi.')}</p><p className="text-muted-foreground">{question?.reason ?? (!response ? "Scrivi liberamente: userò le tue parole per pesare la scelta." : null)}</p></DecisionMessage>
              <div className="pl-[3.125rem]">
                {question?.type === 'single_select' ? <QuickChoice key={`${response?.profileVersion}-${error}`} options={choices.map(choice => choice.label)} onSelect={label => void submit(optionValue(label))} /> :
                question?.type === 'multi_select' ? <PrioritySelector key={`${response?.profileVersion}-${error}`} options={choices.map(choice => choice.label)} max={maxPicks} exclusive={exclusiveLabels} ranked={question.id !== 'constraint_modes'} onConfirm={values => void submit(values.map(optionValue).join(', '))} /> :
                question?.type === 'number' ? <form onSubmit={e => { e.preventDefault(); const data = new FormData(e.currentTarget); void submit(String(data.get('answer'))); }} className="flex flex-wrap gap-3">
                  <label className="sr-only" htmlFor="guided-number">{question.label}</label>
                  <input key={question.id} id="guided-number" name="answer" type="number" required min={question.constraints?.minimum ?? undefined} max={question.constraints?.maximum ?? undefined} step="1" placeholder={question.constraints?.unit ?? 'Valore'} className="h-12 min-w-0 rounded-full border border-border bg-card px-5" />
                  <button type="submit" className="h-12 rounded-full bg-primary px-7 text-primary-foreground">Conferma</button>
                </form> : (!response || question) ? <DecisionBar suggestions={response ? [] : ["Cerco un'auto per la famiglia", "Vorrei spendere poco di gestione", "Sto valutando un'elettrica"]} initialValue={response ? '' : initialQuery} placeholder="Descrivi liberamente cosa cerchi" onSubmit={v => void submit(v)} /> : null}
              </div>
            </StepStage>)}
            {capped && <div role="alert" className="rounded-2xl border border-accent/40 bg-card p-5">
              <p className="font-medium">Hai raggiunto il numero massimo di risposte per questa sessione.</p>
              <p className="mt-2 text-sm text-muted-foreground">{ranking.length > 0
                ? 'Il profilo raccolto finora resta valido: apri il Decision Report per vedere il risultato, oppure inizia una nuova sessione.'
                : 'Per continuare inizia una nuova sessione: ripartirai da un profilo vuoto.'}</p>
              <button type="button" onClick={restart} className="mt-3 underline">Inizia una nuova sessione</button>
            </div>}
            {error && <div role="alert" className="rounded-2xl border border-destructive/30 bg-card p-5"><p>{error}</p>{retryable && <button disabled={busy} onClick={() => void submit(retryable.message)} className="mt-3 underline">Riprova</button>}</div>}
            {response?.previewRanking.status === 'insufficient_inventory' && <p role="status" className="text-sm text-muted-foreground">Nessuna offerta verificata corrisponde al profilo. Puoi modificare budget o utilizzo.</p>}
            {ranking.length > 0 && <button disabled={busy} onClick={() => { if (response) { persist(response); void navigate({ to: '/app/report', search: { s: response.decisionId } }); } }} className="h-12 rounded-full bg-primary px-7 text-[0.95rem] font-medium text-primary-foreground">Mostrami il Decision Report</button>}
            {response && !capped && <DecisionBar placeholder="Aggiungi o correggi un'esigenza" disabled={busy} onSubmit={v => void submit(v)} />}
          </div>
        </div>
        <motion.aside className="min-w-0" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.2, ease: EASE }}><MobilePanel><DecisionProfilePanel known={known} missing={response ? response.missingInformation.map(m => ({ id: m.key, label: labels[m.key] ?? m.reason })) : initialMissing.slice(category === null ? 0 : 1).map(label => ({ id: label, label }))} completion={completion} confidence={confidence} ranking={ranking.slice(0, 3).map(toPreview)} /></MobilePanel></motion.aside>
      </div>
    </main>
  </div>;
}
