-- ============================================================
-- NurseHour – Supabase table setup
-- Run this ONCE in Supabase Dashboard → SQL Editor
-- ============================================================

-- ── app_users (signup sync) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS public.app_users (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  email       text        NOT NULL UNIQUE,
  full_name   text,
  program     text,
  created_at  timestamptz DEFAULT now(),
  updated_at  timestamptz DEFAULT now()
);

-- ── mcq_questions (add-question sync) ───────────────────────
CREATE TABLE IF NOT EXISTS public.mcq_questions (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  question_text       text        NOT NULL,
  option_a            text        NOT NULL,
  option_b            text        NOT NULL,
  option_c            text,
  option_d            text,
  correct_answer      text        NOT NULL CHECK (correct_answer IN ('A','B','C','D')),
  answer_explanation  text,
  topic               text,
  program             text,
  paper               text,
  created_at          timestamptz DEFAULT now()
);

-- ── case_studies ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.case_studies (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  title       text        NOT NULL,
  scenario    text,
  content     text,
  file_url    text,
  created_at  timestamptz DEFAULT now()
);

-- ── books_slides ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.books_slides (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  title       text        NOT NULL,
  description text,
  file_url    text,
  kind        text        NOT NULL CHECK (kind IN ('book','slide')),
  created_at  timestamptz DEFAULT now()
);

-- ── payments ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.payments (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_email  text,
  amount      text        NOT NULL,
  status      text        NOT NULL,
  description text,
  created_at  timestamptz DEFAULT now()
);

-- ── inquiries ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.inquiries (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text        NOT NULL,
  email       text        NOT NULL,
  subject     text,
  message     text        NOT NULL,
  replied_at  timestamptz,
  created_at  timestamptz DEFAULT now()
);

-- ── practice_sessions (every test started/finished from /practice/) ────────────
CREATE TABLE IF NOT EXISTS public.practice_sessions (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  django_session_id  bigint      NOT NULL UNIQUE,
  user_email         text,
  program            text,
  paper              text,
  timed              boolean     DEFAULT false,
  total_questions    int         NOT NULL DEFAULT 0,
  correct_count      int         NOT NULL DEFAULT 0,
  started_at         timestamptz,
  finished_at        timestamptz,
  created_at         timestamptz DEFAULT now()
);

-- ── practice_answers (every answer submitted in a practice test) ──────────────
CREATE TABLE IF NOT EXISTS public.practice_answers (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  django_session_id   bigint      NOT NULL,
  user_email          text,
  question_text       text,
  chosen_answer       text,
  correct_answer      text,
  is_correct          boolean     DEFAULT false,
  program             text,
  paper               text,
  topic               text,
  answered_at         timestamptz,
  created_at          timestamptz DEFAULT now()
);

-- ── RLS: allow service_role / anon to read & write all tables ─
DO $$
DECLARE
  tbl text;
BEGIN
  FOREACH tbl IN ARRAY ARRAY['app_users','mcq_questions','case_studies','books_slides','payments','inquiries','practice_sessions','practice_answers']
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', tbl);
    EXECUTE format(
      'DROP POLICY IF EXISTS "open_access" ON public.%I', tbl);
    EXECUTE format(
      'CREATE POLICY "open_access" ON public.%I FOR ALL USING (true) WITH CHECK (true)', tbl);
  END LOOP;
END;
$$;
