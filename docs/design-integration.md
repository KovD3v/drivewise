# Decision Hub design integration

The frontend copies the ZIP's landing, wizard components, report, vehicle detail,
comparison preview, My DriveWise, legal pages, styles, animations and assets.
Existing collection, search, Advisor and model-analysis routes remain available.

The Guided Decision backend is provided by PR #5
(https://github.com/KovD3v/drivewise/pull/5), not by the base `main` branch.
The car flow requires that backend before deployment; this design import does
not include backend code or database migrations.

| Function | Implementation |
| --- | --- |
| Car catalog and details | Existing `/vehicles` API and canonical IDs |
| Car guided decision | Existing `/guided-decisions` create, versioned turns and reload |
| Ranking and confidence | Backend response; no ZIP scoring engine for cars |
| Vehicle questions | Existing `/advisor/model-analysis` API |
| Documents / Advisor | Links to existing frontend routes |
| Motorcycles and scooters | Explicit mock catalog and fixed demo ranking |
| Reliability / theft presentation | Labelled mock sections, never used for car ranking |
| Accounts, profiles, saved reports, preferences | Browser-local mocks; no Supabase, OAuth or email requests |
| Comparison and future personal-area features | Labelled previews; early-access action is simulated |
| Contact and voice input | Explicit simulation, no outgoing message or recording |

An unavailable existing API produces an error, not a fallback to the ZIP's car
catalog. Existing `VITE_API_BASE_URL` and `VITE_USE_MOCK_API` behavior is preserved
for the original API client. Guided Decision always needs the backend.

The landing hero uses the original artwork downloaded from drivewise-italia.com.
The car intake restores the reference category selection before sending the selected
category and free text to the existing Guided Decision API. Subsequent questions,
confidence and rankings remain backend-owned; the reference's local car scoring
engine is not imported. Initial intake indicators describe collected information
only, as explained in the confidence tooltip. ZIP credentials, Supabase infrastructure and build configuration
were not imported.

Run with `bun run dev:web` and the existing FastAPI server. Verification:
`bun run test:web`, `bun run typecheck:web`, `bun run build:web`.
Browser smoke used the actual FastAPI routes and scoring engine with the existing
test repositories, without a database connection. This does not verify production
catalog contents or database persistence.

## November 2026 design update

The 24/11/2026 Lovable export was merged three ways onto this import: the
13/09 export is the base, this branch is ours, and the November export is
theirs. Design changes arrive, and the API boundaries above stay as they are.

- **Home:** story chapters with vignettes (decision, weights, lifecycle),
  `MotionPause` controls for looping motion, and the shared scroll-reveal
  policy. The September `HeroVision`, `HowItWorks` and `WhyDriveWise` sections
  were replaced by `HeroStory` and its chapters.
- **Home requests:** `wizard-input` infers explicit answers from the home
  request, but only for the local motorcycle and scooter wizard. Car requests
  still go only to `GuidedCarFlow` and the Guided Decision API.
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
