-- Patent Discovery System - PostgreSQL Schema (TRUE MVP)
-- Version: 1.0.0 - Learn MCP First
-- Focus: Ingest USPTO data via MCP server, basic search

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For text search


CREATE SCHEMA IF NOT EXISTS patents;
SET search_path TO patents, public;


-- Patents table
CREATE TABLE patents.patents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patent_number VARCHAR(50) NOT NULL UNIQUE,
    title TEXT NOT NULL,
    abstract TEXT,
    
    filing_date DATE,
    grant_date DATE,
    
    assignee_name TEXT,
    inventor_names TEXT,
    
    raw_data JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_patents_number ON patents.patents(patent_number);
CREATE INDEX idx_patents_title_trgm ON patents.patents USING gin(title gin_trgm_ops);
CREATE INDEX idx_patents_filing_date ON patents.patents(filing_date);


CREATE TABLE patents.claims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patent_id UUID NOT NULL REFERENCES patents.patents(id) ON DELETE CASCADE,
    claim_number INTEGER NOT NULL,
    claim_text TEXT NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_patent_claim UNIQUE(patent_id, claim_number)
);

CREATE INDEX idx_claims_patent_id ON patents.claims(patent_id);
CREATE INDEX idx_claims_text_trgm ON patents.claims USING gin(claim_text gin_trgm_ops);