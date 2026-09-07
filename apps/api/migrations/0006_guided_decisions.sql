CREATE TABLE IF NOT EXISTS guided_decisions (
  id uuid PRIMARY KEY,
  locale text NOT NULL,
  market text NOT NULL,
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'completed', 'abandoned')),
  profile_version integer NOT NULL DEFAULT 1
    CHECK (profile_version >= 1),
  decision_profile jsonb NOT NULL DEFAULT '{}'::jsonb,
  last_response jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (updated_at >= created_at)
);

CREATE TABLE IF NOT EXISTS guided_decision_turns (
  id uuid PRIMARY KEY,
  decision_id uuid NOT NULL
    REFERENCES guided_decisions(id) ON DELETE CASCADE,
  profile_version integer NOT NULL CHECK (profile_version >= 1),
  user_message text NOT NULL,
  assistant_message text NOT NULL,
  updated_fields jsonb NOT NULL DEFAULT '[]'::jsonb,
  profile_snapshot jsonb NOT NULL,
  response_payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (decision_id, profile_version)
);

CREATE INDEX IF NOT EXISTS guided_decision_turns_decision_created_idx
  ON guided_decision_turns (decision_id, created_at);
