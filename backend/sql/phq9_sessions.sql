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
