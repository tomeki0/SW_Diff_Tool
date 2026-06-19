-- Schema dos presets do SW Diff Tool.
-- Rodar no SQL editor do Supabase (ou via psql) uma vez ao criar o projeto.

create extension if not exists "pgcrypto";  -- fornece gen_random_uuid()

create table if not exists presets (
    id        uuid primary key default gen_random_uuid(),
    nome      text not null unique,
    build_id  text not null,
    data      timestamptz not null default now(),
    props     jsonb not null default '{}'::jsonb,
    packages  text not null default '',
    features  text not null default '',
    apk_info  jsonb not null default '{}'::jsonb
);

create index if not exists presets_data_idx on presets (data desc);
