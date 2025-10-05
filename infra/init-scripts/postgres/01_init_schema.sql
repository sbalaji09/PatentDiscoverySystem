-- Patent Discovery System - PostgreSQL Schema
-- Version: 1.0.0

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For text search optimization

-- Create schemas
CREATE SCHEMA IF NOT EXISTS patents;

-- Set search path
SET search_path TO patents, public;

-- ============================================================================
-- ASSIGNEES TABLE
-- Stores information about patent assignees (companies, organizations)
-- ============================================================================
CREATE TABLE patents.assignees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(500) NOT NULL,
    normalized_name VARCHAR(500), -- Normalized version for matching
    organization_type VARCHAR(50), -- company, university, individual, government, etc.
    country VARCHAR(3), -- ISO 3166-1 alpha-3 country code
    address TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_normalized_assignee UNIQUE(normalized_name)
);

CREATE INDEX idx_assignees_name ON patents.assignees USING gin(name gin_trgm_ops);
CREATE INDEX idx_assignees_normalized ON patents.assignees(normalized_name);
CREATE INDEX idx_assignees_country ON patents.assignees(country);

-- ============================================================================
-- INVENTORS TABLE
-- Stores information about patent inventors
-- ============================================================================
CREATE TABLE patents.inventors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name VARCHAR(255),
    last_name VARCHAR(255) NOT NULL,
    full_name VARCHAR(500) NOT NULL,
    normalized_name VARCHAR(500), -- Normalized version for matching
    country VARCHAR(3), -- ISO 3166-1 alpha-3 country code
    city VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_normalized_inventor UNIQUE(normalized_name)
);

CREATE INDEX idx_inventors_full_name ON patents.inventors USING gin(full_name gin_trgm_ops);
CREATE INDEX idx_inventors_last_name ON patents.inventors(last_name);
CREATE INDEX idx_inventors_normalized ON patents.inventors(normalized_name);

-- ============================================================================
-- PATENTS TABLE
-- Main table storing patent metadata
-- ============================================================================
CREATE TABLE patents.patents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patent_number VARCHAR(50) NOT NULL UNIQUE, -- e.g., US-10123456-B2
    publication_number VARCHAR(50), -- Publication number if different
    application_number VARCHAR(50),
    title TEXT NOT NULL,
    abstract TEXT,
    filing_date DATE,
    publication_date DATE,
    grant_date DATE,
    country VARCHAR(3) NOT NULL, -- ISO 3166-1 alpha-3
    patent_type VARCHAR(50), -- utility, design, plant, reissue, etc.
    status VARCHAR(50), -- active, expired, abandoned, pending, etc.

    -- Classification codes
    ipc_codes TEXT[], -- International Patent Classification
    cpc_codes TEXT[], -- Cooperative Patent Classification
    uspc_codes TEXT[], -- US Patent Classification (legacy)

    -- Citation counts (denormalized for performance)
    cited_by_count INTEGER DEFAULT 0,
    cites_count INTEGER DEFAULT 0,

    -- Full text (for search)
    description TEXT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_filing_date CHECK (filing_date <= COALESCE(grant_date, CURRENT_DATE)),
    CONSTRAINT valid_publication_date CHECK (publication_date >= filing_date)
);

CREATE INDEX idx_patents_number ON patents.patents(patent_number);
CREATE INDEX idx_patents_publication_number ON patents.patents(publication_number);
CREATE INDEX idx_patents_application_number ON patents.patents(application_number);
CREATE INDEX idx_patents_filing_date ON patents.patents(filing_date);
CREATE INDEX idx_patents_grant_date ON patents.patents(grant_date);
CREATE INDEX idx_patents_country ON patents.patents(country);
CREATE INDEX idx_patents_status ON patents.patents(status);
CREATE INDEX idx_patents_ipc_codes ON patents.patents USING gin(ipc_codes);
CREATE INDEX idx_patents_cpc_codes ON patents.patents USING gin(cpc_codes);
CREATE INDEX idx_patents_title ON patents.patents USING gin(title gin_trgm_ops);
CREATE INDEX idx_patents_abstract ON patents.patents USING gin(abstract gin_trgm_ops);

-- ============================================================================
-- CLAIMS TABLE
-- Stores individual patent claims
-- ============================================================================
CREATE TABLE patents.claims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patent_id UUID NOT NULL REFERENCES patents.patents(id) ON DELETE CASCADE,
    claim_number INTEGER NOT NULL,
    claim_text TEXT NOT NULL,
    claim_type VARCHAR(20) NOT NULL, -- independent, dependent
    depends_on_claim INTEGER, -- For dependent claims
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_patent_claim UNIQUE(patent_id, claim_number),
    CONSTRAINT valid_claim_number CHECK (claim_number > 0),
    CONSTRAINT valid_dependency CHECK (
        (claim_type = 'independent' AND depends_on_claim IS NULL) OR
        (claim_type = 'dependent' AND depends_on_claim IS NOT NULL AND depends_on_claim < claim_number)
    )
);

CREATE INDEX idx_claims_patent_id ON patents.claims(patent_id);
CREATE INDEX idx_claims_claim_number ON patents.claims(patent_id, claim_number);
CREATE INDEX idx_claims_type ON patents.claims(claim_type);
CREATE INDEX idx_claims_text ON patents.claims USING gin(claim_text gin_trgm_ops);

-- ============================================================================
-- PATENT_ASSIGNEES (Junction Table)
-- Many-to-many relationship between patents and assignees
-- ============================================================================
CREATE TABLE patents.patent_assignees (
    patent_id UUID NOT NULL REFERENCES patents.patents(id) ON DELETE CASCADE,
    assignee_id UUID NOT NULL REFERENCES patents.assignees(id) ON DELETE CASCADE,
    sequence INTEGER DEFAULT 1, -- Order of assignees
    assignment_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (patent_id, assignee_id)
);

CREATE INDEX idx_patent_assignees_patent ON patents.patent_assignees(patent_id);
CREATE INDEX idx_patent_assignees_assignee ON patents.patent_assignees(assignee_id);

-- ============================================================================
-- PATENT_INVENTORS (Junction Table)
-- Many-to-many relationship between patents and inventors
-- ============================================================================
CREATE TABLE patents.patent_inventors (
    patent_id UUID NOT NULL REFERENCES patents.patents(id) ON DELETE CASCADE,
    inventor_id UUID NOT NULL REFERENCES patents.inventors(id) ON DELETE CASCADE,
    sequence INTEGER DEFAULT 1, -- Order of inventors
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (patent_id, inventor_id)
);

CREATE INDEX idx_patent_inventors_patent ON patents.patent_inventors(patent_id);
CREATE INDEX idx_patent_inventors_inventor ON patents.patent_inventors(inventor_id);

-- ============================================================================
-- PATENT_CITATIONS (Citation relationships)
-- Stores which patents cite which other patents
-- ============================================================================
CREATE TABLE patents.patent_citations (
    citing_patent_id UUID NOT NULL REFERENCES patents.patents(id) ON DELETE CASCADE,
    cited_patent_id UUID NOT NULL REFERENCES patents.patents(id) ON DELETE CASCADE,
    citation_type VARCHAR(50), -- examiner, applicant, third-party
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (citing_patent_id, cited_patent_id),
    CONSTRAINT no_self_citation CHECK (citing_patent_id != cited_patent_id)
);

CREATE INDEX idx_citations_citing ON patents.patent_citations(citing_patent_id);
CREATE INDEX idx_citations_cited ON patents.patent_citations(cited_patent_id);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION patents.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers
CREATE TRIGGER update_patents_updated_at BEFORE UPDATE ON patents.patents
    FOR EACH ROW EXECUTE FUNCTION patents.update_updated_at_column();

CREATE TRIGGER update_assignees_updated_at BEFORE UPDATE ON patents.assignees
    FOR EACH ROW EXECUTE FUNCTION patents.update_updated_at_column();

CREATE TRIGGER update_inventors_updated_at BEFORE UPDATE ON patents.inventors
    FOR EACH ROW EXECUTE FUNCTION patents.update_updated_at_column();

-- Update citation counts trigger
CREATE OR REPLACE FUNCTION patents.update_citation_counts()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Increment cited_by_count for the cited patent
        UPDATE patents.patents
        SET cited_by_count = cited_by_count + 1
        WHERE id = NEW.cited_patent_id;

        -- Increment cites_count for the citing patent
        UPDATE patents.patents
        SET cites_count = cites_count + 1
        WHERE id = NEW.citing_patent_id;

    ELSIF TG_OP = 'DELETE' THEN
        -- Decrement cited_by_count for the cited patent
        UPDATE patents.patents
        SET cited_by_count = GREATEST(cited_by_count - 1, 0)
        WHERE id = OLD.cited_patent_id;

        -- Decrement cites_count for the citing patent
        UPDATE patents.patents
        SET cites_count = GREATEST(cites_count - 1, 0)
        WHERE id = OLD.citing_patent_id;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_citation_counts_trigger
AFTER INSERT OR DELETE ON patents.patent_citations
FOR EACH ROW EXECUTE FUNCTION patents.update_citation_counts();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View for complete patent information with related entities
CREATE OR REPLACE VIEW patents.patents_complete AS
SELECT
    p.*,
    ARRAY_AGG(DISTINCT i.full_name ORDER BY i.full_name) FILTER (WHERE i.id IS NOT NULL) as inventors,
    ARRAY_AGG(DISTINCT a.name ORDER BY a.name) FILTER (WHERE a.id IS NOT NULL) as assignees
FROM patents.patents p
LEFT JOIN patents.patent_inventors pi ON p.id = pi.patent_id
LEFT JOIN patents.inventors i ON pi.inventor_id = i.id
LEFT JOIN patents.patent_assignees pa ON p.id = pa.patent_id
LEFT JOIN patents.assignees a ON pa.assignee_id = a.id
GROUP BY p.id;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON SCHEMA patents IS 'Patent Discovery System - Main schema for patent data';
COMMENT ON TABLE patents.patents IS 'Core patent metadata and full text';
COMMENT ON TABLE patents.claims IS 'Individual patent claims';
COMMENT ON TABLE patents.inventors IS 'Patent inventors (deduplicated)';
COMMENT ON TABLE patents.assignees IS 'Patent assignees/owners (deduplicated)';
COMMENT ON TABLE patents.patent_citations IS 'Patent-to-patent citation relationships';
