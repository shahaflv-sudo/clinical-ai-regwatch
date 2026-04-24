-- Add drafts table for History feature.
-- Run this once in Supabase SQL Editor.

create table if not exists drafts (
    id            bigserial primary key,
    user_request  text        not null,
    system_prompt text,
    language      text        not null,
    draft_text    text        not null,
    source_ids    bigint[]    not null default '{}',
    created_at    timestamptz not null default now()
);

create index if not exists drafts_created_at_idx on drafts (created_at desc);
