-- PHQ-9 protocol runtime state
-- Run this in Supabase SQL editor.

create table if not exists public.phq9_sessions (
  id text primary key,                 -- "{user_id}:{conversation_id}"
  user_id text not null,
  conversation_id text not null,
  protocol_state jsonb,
  total_score integer,
  severity_level text,
  protocol_completed boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_phq9_sessions_user_id
  on public.phq9_sessions (user_id);

alter table public.phq9_sessions
  drop constraint if exists phq9_sessions_total_score_range;

alter table public.phq9_sessions
  add constraint phq9_sessions_total_score_range check (
    total_score is null or total_score between 0 and 27
  );

alter table public.phq9_sessions
  drop constraint if exists phq9_sessions_severity_values;

alter table public.phq9_sessions
  add constraint phq9_sessions_severity_values check (
    severity_level is null
    or severity_level in ('minimal', 'mild', 'moderate', 'moderately_severe', 'severe')
  );
