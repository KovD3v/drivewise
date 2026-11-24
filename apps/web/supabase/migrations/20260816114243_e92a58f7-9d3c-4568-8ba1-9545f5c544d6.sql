CREATE TABLE public.saved_analyses (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  session_id TEXT,
  vehicle_id TEXT NOT NULL,
  brand TEXT NOT NULL,
  model TEXT NOT NULL,
  category TEXT,
  vehicle_type TEXT,
  score INTEGER NOT NULL DEFAULT 0,
  confidence INTEGER NOT NULL DEFAULT 0,
  tags TEXT[] NOT NULL DEFAULT '{}',
  profile JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.saved_analyses TO authenticated;
GRANT ALL ON public.saved_analyses TO service_role;

ALTER TABLE public.saved_analyses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own saved analyses"
  ON public.saved_analyses FOR SELECT TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own saved analyses"
  ON public.saved_analyses FOR INSERT TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own saved analyses"
  ON public.saved_analyses FOR UPDATE TO authenticated
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own saved analyses"
  ON public.saved_analyses FOR DELETE TO authenticated
  USING (auth.uid() = user_id);

CREATE INDEX saved_analyses_user_created_idx ON public.saved_analyses (user_id, created_at DESC);