-- Add content-hash dedup so the weekly scraper skips unchanged docs.
-- Run once in Supabase SQL Editor.

create extension if not exists pgcrypto;

alter table documents add column if not exists content_hash text;
alter table documents add column if not exists last_changed_at timestamptz;

create index if not exists documents_last_changed_idx on documents (last_changed_at desc);

-- Backfill: compute hash for the 199 existing docs so the first weekly run skips them all.
-- Hash matches what pipeline/run_weekly.py computes: sha256 of (raw_text or title), stripped.
update documents
   set content_hash = encode(digest(trim(coalesce(nullif(raw_text, ''), title)), 'sha256'), 'hex'),
       last_changed_at = coalesce(last_changed_at, scraped_at)
 where content_hash is null;
