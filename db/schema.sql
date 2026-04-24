-- Clinical AI RegWatch — Supabase schema
-- Run this once in Supabase SQL Editor (Project -> SQL Editor -> New query -> paste -> Run)

create extension if not exists vector;

create table if not exists documents (
    id              bigserial primary key,
    source          text        not null,           -- 'fda', 'moh_il', 'ema', 'mhra', 'who', ...
    source_id       text        not null,           -- stable id within source (URL hash, doc number)
    url             text        not null,
    title           text        not null,
    raw_text        text,
    summary         text,                           -- Gemini-generated 1-paragraph summary
    why_care        text,                           -- "why the regulation lead should care"
    category        text,                           -- Procurement / Development / Ethics / Security / Clinical Validation / Other
    region          text,                           -- US / EU / IL / UK / Global
    published_at    timestamptz,                    -- date the source published it
    scraped_at      timestamptz not null default now(),
    embedding       vector(768),                    -- Gemini text-embedding-004
    metadata        jsonb       not null default '{}'::jsonb,

    unique (source, source_id)
);

create index if not exists documents_scraped_at_idx
    on documents (scraped_at desc);

create index if not exists documents_category_region_idx
    on documents (category, region);

create index if not exists documents_published_at_idx
    on documents (published_at desc);

-- HNSW index for cosine similarity search on embeddings.
-- Built only after the table has data; safe to create now (will be empty).
create index if not exists documents_embedding_hnsw_idx
    on documents using hnsw (embedding vector_cosine_ops);
