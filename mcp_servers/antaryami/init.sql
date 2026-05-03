-- Run once in Supabase SQL editor to set up pgvector tables and functions.

create extension if not exists vector;

create table if not exists doc_chunks (
    id          uuid primary key default gen_random_uuid(),
    doc_id      text not null,
    title       text not null default '',
    chunk_index integer not null default 0,
    content     text not null,
    embedding   vector(1536),
    metadata    jsonb not null default '{}',
    created_at  timestamptz not null default now()
);

create index if not exists doc_chunks_doc_id_idx
    on doc_chunks(doc_id);

create index if not exists doc_chunks_embedding_idx
    on doc_chunks using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

create or replace function match_doc_chunks(
    query_embedding vector(1536),
    match_count     int default 5
) returns table (
    id          uuid,
    doc_id      text,
    title       text,
    chunk_index integer,
    content     text,
    similarity  float
) language sql stable as $$
    select id, doc_id, title, chunk_index, content,
           1 - (embedding <=> query_embedding) as similarity
    from   doc_chunks
    order  by embedding <=> query_embedding
    limit  match_count;
$$;

create or replace function match_doc_chunks_filtered(
    query_embedding vector(1536),
    match_count     int default 5,
    filter_doc_id   text default null
) returns table (
    id          uuid,
    doc_id      text,
    title       text,
    chunk_index integer,
    content     text,
    similarity  float
) language sql stable as $$
    select id, doc_id, title, chunk_index, content,
           1 - (embedding <=> query_embedding) as similarity
    from   doc_chunks
    where  (filter_doc_id is null or doc_id = filter_doc_id)
    order  by embedding <=> query_embedding
    limit  match_count;
$$;
