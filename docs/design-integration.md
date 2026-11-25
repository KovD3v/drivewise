# Decision Hub design integration

The frontend copies the ZIP's landing, wizard components, report, vehicle detail,
comparison preview, My DriveWise, legal pages, styles, animations and assets.
The earlier MVP pages (`/vehicles`, `/listings`, `/documents`, `/search`,
`/advisor`, `/model-analysis`) were removed from the site; the Decision Hub
routes listed in [`architecture.md`](architecture.md) are the whole site.

The Guided Decision backend (PR #5) and the unified API-first build (PR #22)
are on `main`. The car flow therefore runs against the deployed API, and the
site and API ship together as one Vercel project (`vercel.json`).

| Function | Implementation |
| --- | --- |
| Car catalog and details | `GET /vehicles` and `GET /vehicles/{id}` with canonical IDs; `?spec=` on the vehicle page keeps the chosen variant |
| List price and sources | `list_price` and `provenance` of the API, labelled "Prezzo di listino" with date, notes, a link and source credits |
| Car guided decision | `/guided-decisions` create, versioned turns and reload |
| Decision report | `/app/report?s=<decision id>` loads `GET /guided-decisions/{id}` directly, so a shared or reopened link works without `localStorage`; the API recomputes the ranking on every read, so it follows the current catalogue and source permissions |
| Ranking and confidence | Backend response; no ZIP scoring engine for cars |
| Vehicle questions | `POST /advisor/model-analysis`, for the variant named by `?spec=` |
| Report actions | Both report CTAs are enabled: one opens the winner's vehicle page with `spec` and `s`, the other restarts the guided choice; alternatives also link with `spec` and `s` |
| Motorcycles and scooters | `/app/catalog?type=` from `GET /vehicles?vehicle_type=`, without a score |
| Accounts, profiles, saved reports, preferences | Browser-local mocks; no Supabase, OAuth or email requests |
| Comparison | `/app/compare?vehicle=&with=` (with `spec` and `withSpec`): two vehicles of one type from the API |
| Future personal-area features | Labelled previews; early-access action is simulated |
| Contact and voice input | Explicit simulation, no outgoing message or recording |
| Fonts | Inter and Manrope are self-hosted from `apps/web/public/fonts/` (SIL OFL 1.1); the site makes no request to Google Fonts |

An unavailable existing API produces an error, not a fallback to the ZIP's car
catalog. The site has no mock API: `VITE_API_BASE_URL` names the API, and Guided
Decision always needs the backend. The bundled two-wheel dataset, its fixed scores
and the theft and reliability previews were removed (`feat/unified-demo`).

The landing hero uses the original artwork downloaded from drivewise-italia.com.
The car intake restores the reference category selection before sending the selected
category and free text to the existing Guided Decision API. Subsequent questions,
confidence and rankings remain backend-owned; the reference's local car scoring
engine is not imported. Initial intake indicators describe collected information
only, as explained in the confidence tooltip. ZIP credentials, Supabase infrastructure and build configuration
were not imported.

Run with `bun run dev:web` and the FastAPI server. Verification:
`bun run test:web`, `bun run typecheck:web`, `bun run build:web`; CI runs the
same checks on Node 22 (`.nvmrc`). The web types come from the API's OpenAPI
schema (`bun run gen:api-types`), and CI fails when they drift.

## November 2026 design update

The 24/11/2026 Lovable export was merged three ways onto this import: the
13/09 export is the base, this branch is ours, and the November export is
theirs. Design changes arrive, and the API boundaries above stay as they are.

- **Home:** story chapters with vignettes (decision, weights, lifecycle),
  `MotionPause` controls for looping motion, and the shared scroll-reveal
  policy. The September `HeroVision`, `HowItWorks` and `WhyDriveWise` sections
  were replaced by `HeroStory` and its chapters.
- **Home requests:** `wizard-input` infers only the vehicle type from the home
  request. Car requests go to `GuidedCarFlow` and the Guided Decision API;
  motorcycle and scooter requests open the catalogue.
- **Contact:** the split layout with reason-specific fields, a live ticket,
  FAQ suggestions and a receipt. Lovable saved requests to Supabase through a
  server function. Here `src/lib/contact-demo.ts` validates the form and shows
  a `DEMO-…` receipt labelled as simulated; nothing is sent or stored.
- **Accounts:** the browser-local demo account from this branch stays.
  Lovable's Google/Apple broker and Supabase auth were not imported.
- **Labels and metadata:** Italian category labels (`category-labels`), SEO and
  social meta tags, the favicon, and `apple-touch-icon.png` and
  `drivewise-social.png` in `public/`. Lovable hosted these images behind
  `*.asset.json` pointers; the files now come from drivewise-italia.com.
- **New UI primitives:** `button`, `checkbox` and `switch`, with their Radix
  dependencies.
