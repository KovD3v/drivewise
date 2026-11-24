CREATE TABLE public.contact_requests (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 request_code text NOT NULL UNIQUE,
 email text NOT NULL,
 payload jsonb NOT NULL,
 response_due date NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
GRANT ALL ON public.contact_requests TO service_role;
ALTER TABLE public.contact_requests ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service can manage contact requests" ON public.contact_requests FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE INDEX contact_requests_email_time ON public.contact_requests (email, created_at);
CREATE FUNCTION public.submit_contact_request(p_email text, p_payload jsonb, p_due date) RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE code text;
BEGIN
 PERFORM pg_advisory_xact_lock(hashtextextended(lower(p_email), 0));
 IF (SELECT count(*) FROM public.contact_requests WHERE email = lower(p_email) AND created_at > now() - interval '1 hour') >= 5 THEN
  RAISE EXCEPTION 'Too many requests';
 END IF;
 code := 'DW-' || to_char(now() AT TIME ZONE 'Europe/Rome', 'YYMM') || '-' || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 8));
 INSERT INTO public.contact_requests (request_code, email, payload, response_due) VALUES (code, lower(p_email), p_payload, p_due);
 RETURN code;
END;
$$;
REVOKE ALL ON FUNCTION public.submit_contact_request(text, jsonb, date) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.submit_contact_request(text, jsonb, date) TO service_role;