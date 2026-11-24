# Supabase per `apps/web` (uscita da Lovable)

Questa nota spiega come far girare il frontend DriveWise su un progetto Supabase nostro, invece di quello gestito da Lovable Cloud, in vista del deploy su Vercel.

## 1. Situazione attuale

- Il codice in `apps/web` è l'export di Lovable del 24/11/2026 (TanStack Start + React 19 + Supabase).
- Il progetto Supabase usato oggi in produzione (`zsajekiqalfcjnixnigz`) **è gestito da Lovable Cloud**: non è in un nostro account Supabase, quindi non abbiamo dashboard né `service_role` key.
- Il catalogo veicoli **non sta su Supabase**: è il JSON statico `src/data/drivewise/functional-v1/vehicles.json`. Supabase serve solo per:

| Tabella | Uso | Accesso |
|---|---|---|
| `profiles` | nome, consensi privacy/marketing; creata da trigger alla registrazione | utente loggato, solo la propria riga (RLS) |
| `saved_analyses` | Decision Report salvati in My DriveWise | utente loggato, solo le proprie righe (RLS) |
| `contact_requests` | richieste dal modulo Contatti | solo `service_role`, tramite la funzione `submit_contact_request` (limite di 5 richieste/ora per email) |

## 2. Creare il progetto Supabase

1. Crea un nuovo progetto su supabase.com, in una regione UE (es. `eu-central-1`, Francoforte).
2. Applica lo schema **in quest'ordine**:
   1. `supabase/migrations/20260816114243_…sql` → `saved_analyses`
   2. `supabase/migrations/20260911191913_…sql` → `profiles`, trigger `handle_new_user`
   3. `supabase/migrations/20260911191922_…sql` → revoca di `execute` su `handle_new_user`
   4. `drizzle/migrations/0000_create_contact_requests.sql` → `contact_requests` e `submit_contact_request`

   La quarta migrazione sta fuori da `supabase/migrations` perché Lovable la applicava con Drizzle. Il modo più semplice è spostarla lì con un timestamp successivo (es. `20260913000000_create_contact_requests.sql`) e poi:

   ```bash
   cd apps/web
   npx supabase link --project-ref <REF>
   npx supabase db push
   ```

   In alternativa puoi incollare i 4 file, nello stesso ordine, nell'SQL Editor della dashboard.
3. Rigenera i tipi TypeScript dal nuovo progetto:

   ```bash
   npx supabase gen types typescript --project-id <REF> > src/integrations/supabase/types.ts
   ```

4. Aggiorna `supabase/config.toml` con il nuovo `project_id`.

## 3. Variabili d'ambiente

| Variabile | Dove serve | Segreta? |
|---|---|---|
| `VITE_SUPABASE_URL` | browser (inserita a build time) | no |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | browser (chiave `sb_publishable_…`) | no |
| `SUPABASE_URL` | server (SSR, server functions) | no |
| `SUPABASE_PUBLISHABLE_KEY` | server | no |
| `SUPABASE_SERVICE_ROLE_KEY` | server, **solo** per il modulo Contatti (`src/lib/contact.functions.ts`) | **sì**: mai con prefisso `VITE_` |

- **In locale:** crea `apps/web/.env` con queste variabili. `.env` è in `.gitignore`, non va mai committato.
- **Su Vercel:** Project → Settings → Environment Variables, con gli stessi valori per Production e Preview.

Senza `SUPABASE_SERVICE_ROLE_KEY` il sito funziona, ma l'invio del modulo Contatti fallisce con un messaggio di errore.

## 4. Autenticazione

**Email + password** funziona così com'è con Supabase Auth. In Authentication → URL Configuration imposta:

- **Site URL:** il dominio di produzione (es. `https://drivewise.it`).
- **Redirect URLs:** `http://localhost:3000/**`, il dominio di produzione e quello delle preview Vercel (es. `https://*-<team>.vercel.app/**`).

**Google / Apple da cambiare.** Oggi passano dal broker OAuth di Lovable (`src/integrations/lovable/index.ts`, `@lovable.dev/cloud-auth-js`), che fuori da Lovable non funziona. Per sistemarli:

1. Abilita i provider in Authentication → Providers, con le credenziali OAuth di Google Cloud e dell'Apple Developer.
2. In `src/components/auth/AuthDialog.tsx` sostituisci `lovable.auth.signInWithOAuth(provider, …)` con:

   ```ts
   await supabase.auth.signInWithOAuth({
     provider, // "google" | "apple"
     options: { redirectTo: `${window.location.origin}/app/me` },
   });
   ```

3. Elimina `src/integrations/lovable/` e la dipendenza `@lovable.dev/cloud-auth-js`.

**`previewAuthStorage.ts`** sincronizza la sessione con l'editor di Lovable solo sui domini Lovable; altrove usa `localStorage`. Si può lasciare, oppure togliere `storage: brokeredPreviewStorage()` da `src/integrations/supabase/client.ts` per usare lo storage di default.

## 5. Dati esistenti

I dati del progetto Lovable Cloud (utenti, analisi salvate, richieste di contatto) **non si trasferiscono da soli**.

- Le tabelle si possono esportare in CSV dalla vista Cloud di Lovable e reimportare.
- Gli account utente invece non si spostano con le password: gli utenti dovranno registrarsi di nuovo, oppure si chiede a Lovable l'export di `auth.users`.

Da decidere con Andrea se conservarli o ripartire da zero.

## 6. Note per il deploy su Vercel

- **Configurazione:** `vercel.json` nella root serve già `apps/web` come servizio `web` (framework `tanstack-start`) accanto all'API. Questo frontend per ora non chiama l'API: il catalogo arriva dal JSON statico.
- **Build:** `vite.config.ts` usa `@lovable.dev/vite-tanstack-config`, che include già Nitro. In locale compila per Cloudflare, ma con `VERCEL=1` (cioè su Vercel) Nitro sceglie da solo il preset `vercel` e scrive `.vercel/output`: l'ho verificato. Più avanti conviene comunque sostituire la config Lovable con quella standard di TanStack Start più `nitro()`, come nella versione precedente di `apps/web`.
- **TanStack:** aggiornato a `@tanstack/react-start@1.169.7` e `@tanstack/react-router@1.170.46`, le versioni che correggono CVE-2026-102989. In `src/lib/contact.functions.ts`, `.inputValidator()` è diventato `.validator()`.
- **Tipi API:** `src/api/schema.gen.ts` e lo script `gen:api-types` restano, così il controllo del CI continua a funzionare e i tipi sono pronti quando collegheremo il frontend all'API.
- **Error reporting:** `src/lib/lovable-error-reporting.ts` invia gli errori a Lovable e fuori da Lovable non fa nulla. Va sostituito con Sentry o simili, quando serve.
