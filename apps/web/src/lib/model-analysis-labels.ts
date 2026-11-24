/** Italian labels for the codes and assumptions returned by POST /advisor/model-analysis. */
const resultLabels: Record<string, string> = {
  asking_price_eur: 'Prezzo richiesto',
  current_km: 'Chilometraggio attuale',
  above_range: 'Sopra la fascia di mercato',
  asking_price_above_market_reference: 'Prezzo richiesto sopra il riferimento',
  asking_price_above_reference: 'Prezzo sopra il riferimento',
  asking_price_below_market_reference: 'Prezzo richiesto sotto il riferimento',
  below_range: 'Sotto la fascia di mercato',
  check_battery_health_report: 'Verifica il report sullo stato della batteria',
  check_hybrid_system_diagnostics: 'Controlla la diagnostica del sistema ibrido',
  compare_alternatives: 'Confronta alternative',
  completed: 'Completata',
  confirm_no_warning_lights: 'Verifica che non ci siano spie accese',
  generate_report: 'Genera report',
  high_mileage_for_age: 'Chilometraggio elevato per l’età',
  in_range: 'In linea con il mercato',
  inspect_brakes_and_tires: 'Controlla freni e pneumatici',
  interesting_with_checks: 'Interessante, con verifiche consigliate',
  low_confidence: 'Bassa affidabilità',
  modify_parameters: 'Modifica parametri',
  needs_input: 'Servono altri dati',
  negotiate_against_reference_price: 'Negozia usando il prezzo di riferimento',
  not_enough_data: 'Dati insufficienti',
  open_checklist: 'Apri checklist',
  requested_spec_not_found: 'Versione richiesta non trovata',
  resolved_spec: 'Versione del veicolo',
  resolved_spec_missing: 'Versione del veicolo non disponibile',
  risky_at_price: 'Rischiosa al prezzo richiesto',
  test_transmission_shift_quality: 'Prova la qualità delle cambiate',
  unknown: 'Non disponibile',
  verify_service_history: 'Verifica lo storico della manutenzione',
  vehicle_resolution_ambiguous: 'Identificazione del veicolo ambigua',
  vehicle_resolution_no_match: 'Nessun veicolo corrispondente',
}

const assumptionLabels: Record<string, string> = {
  'No live market sources are used in Model Analysis V1.':
    'L’analisi V1 non usa fonti di mercato in tempo reale.',
  'Reference prices use eligible, fresh offers for the selected variant.':
    'Il prezzo di riferimento è la media delle offerte recenti per questa versione.',
  'No eligible offer was found, so the reference price is the list price of the selected variant.':
    'Non ci sono offerte valide. Il prezzo di riferimento è il prezzo di listino di questa versione.',
  "No eligible offer or variant list price was found, so the reference price is the model's base price.":
    'Non ci sono offerte valide né un prezzo di listino per questa versione. Il prezzo di riferimento è il prezzo base del modello.',
  'No reference price is available: no eligible offer and no list price.':
    'Non abbiamo un prezzo di riferimento: mancano offerte valide e prezzo di listino.',
  'Annual kilometres are estimated deterministically from usage_profile.':
    'I chilometri annui sono stimati in modo deterministico dal profilo di utilizzo.',
  'Fuel is estimated at EUR 1.85/L and electricity at EUR 0.30/kWh.':
    'Il carburante è stimato a 1,85 €/L e l’elettricità a 0,30 €/kWh.',
  'Maintenance is a heuristic based on body style, powertrain, age, and mileage.':
    'La manutenzione è una stima basata su carrozzeria, alimentazione, età e chilometraggio.',
  'Three-year depreciation is estimated at 28% of the available price.':
    'La svalutazione a tre anni è stimata al 28% del prezzo disponibile.',
}

export function formatResultLabel(value: string) {
  return resultLabels[value] ?? value.replaceAll('_', ' ')
}

export function formatAssumption(value: string) {
  return assumptionLabels[value] ?? value
}
