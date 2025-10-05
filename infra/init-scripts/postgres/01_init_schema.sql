-- Patent Discovery System - PostgreSQL Schema
-- Version: 1.0.0

CREATE EXTENSION vector;

CREATE TABLE patents (
    id UUID PRIMARY KEY,
    patent_number VARCHAR(50) UNIQUE,
    title TEXT,
    abstract TEXT
);

CREATE TABLE claims (
    id UUID PRIMARY KEY,
    patent_id UUID REFERENCES patents(id),
    claim_number INTEGER,
    claim_text TEXT,
    embedding vector(1536), -- for OpenAI embeddings
    
    UNIQUE(patent_id, claim_number)
);

CREATE INDEX ON claims USING ivfflat (embedding vector_cosine_ops);