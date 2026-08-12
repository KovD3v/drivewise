# DriveWise — Decision Engine Integration Architecture

## Target MVP

```text
Lovable frontend
      |
      | HTTPS / JSON
      v
FastAPI backend (/api/v1)
      |
      +-- Decision Session Service
      +-- Decision Service
      +-- Vehicle Service
      |
      v
Decision Engine Python v1.0
      |
      v
Vehicle Repository
      |
      +-- MVP: versioned JSON fixture
      +-- Next: PostgreSQL / validated catalog
```

## Boundary rules
- Lovable never reproduces scoring formulas.
- FastAPI owns HTTP, validation, session orchestration and response DTOs.
- Decision Engine owns deterministic decision science only.
- Vehicle Repository abstracts JSON vs DB.
- Generative AI is an optional explanation/input-extraction service outside ranking.

## First vertical slice
1. Lovable submits structured Decision Profile.
2. FastAPI validates request.
3. Decision Service loads candidate vehicles.
4. Python engine returns ranked result/exclusions/explainability.
5. FastAPI returns DTO.
6. Lovable renders existing Decision Report.

## Why this architecture
- one source of truth for scoring;
- independent engine testing;
- easier calibration/versioning;
- future clients reuse same service;
- Lovable remains replaceable frontend technology.
