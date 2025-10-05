-- Patent Discovery System - Sample Seed Data
-- Version: 1.0.0

SET search_path TO patents, public;

-- ============================================================================
-- SAMPLE DATA (for testing and development)
-- ============================================================================

-- Insert sample assignees
INSERT INTO patents.assignees (id, name, normalized_name, organization_type, country) VALUES
    ('a1111111-1111-1111-1111-111111111111', 'Apple Inc.', 'apple_inc', 'company', 'USA'),
    ('a2222222-2222-2222-2222-222222222222', 'Google LLC', 'google_llc', 'company', 'USA'),
    ('a3333333-3333-3333-3333-333333333333', 'Microsoft Corporation', 'microsoft_corporation', 'company', 'USA'),
    ('a4444444-4444-4444-4444-444444444444', 'Samsung Electronics', 'samsung_electronics', 'company', 'KOR'),
    ('a5555555-5555-5555-5555-555555555555', 'IBM Corporation', 'ibm_corporation', 'company', 'USA')
ON CONFLICT (normalized_name) DO NOTHING;

-- Insert sample inventors
INSERT INTO patents.inventors (id, first_name, last_name, full_name, normalized_name, country) VALUES
    ('b1111111-1111-1111-1111-111111111111', 'John', 'Doe', 'John Doe', 'john_doe', 'USA'),
    ('b2222222-2222-2222-2222-222222222222', 'Jane', 'Smith', 'Jane Smith', 'jane_smith', 'USA'),
    ('b3333333-3333-3333-3333-333333333333', 'Robert', 'Johnson', 'Robert Johnson', 'robert_johnson', 'GBR'),
    ('b4444444-4444-4444-4444-444444444444', 'Maria', 'Garcia', 'Maria Garcia', 'maria_garcia', 'ESP'),
    ('b5555555-5555-5555-5555-555555555555', 'Wei', 'Zhang', 'Wei Zhang', 'wei_zhang', 'CHN')
ON CONFLICT (normalized_name) DO NOTHING;

-- Note: Uncomment below to add sample patents
-- WARNING: This is only for development/testing purposes

/*
-- Insert sample patents
INSERT INTO patents.patents (
    id, patent_number, title, abstract, filing_date, publication_date, grant_date,
    country, patent_type, status, ipc_codes, cpc_codes
) VALUES
    (
        'c1111111-1111-1111-1111-111111111111',
        'US-10000001-B2',
        'Method and System for Data Processing',
        'An improved method for processing large-scale data using distributed computing techniques...',
        '2020-01-15', '2021-01-15', '2022-01-15',
        'USA', 'utility', 'active',
        ARRAY['G06F', 'G06N'], ARRAY['G06F9/50', 'G06N3/08']
    ),
    (
        'c2222222-2222-2222-2222-222222222222',
        'US-10000002-B2',
        'Wireless Communication Device',
        'A novel wireless communication device with enhanced signal processing capabilities...',
        '2019-06-10', '2020-06-10', '2021-06-10',
        'USA', 'utility', 'active',
        ARRAY['H04W', 'H04L'], ARRAY['H04W4/80', 'H04L5/00']
    )
ON CONFLICT (patent_number) DO NOTHING;

-- Link patents to assignees
INSERT INTO patents.patent_assignees (patent_id, assignee_id, sequence) VALUES
    ('c1111111-1111-1111-1111-111111111111', 'a1111111-1111-1111-1111-111111111111', 1),
    ('c2222222-2222-2222-2222-222222222222', 'a2222222-2222-2222-2222-222222222222', 1)
ON CONFLICT DO NOTHING;

-- Link patents to inventors
INSERT INTO patents.patent_inventors (patent_id, inventor_id, sequence) VALUES
    ('c1111111-1111-1111-1111-111111111111', 'b1111111-1111-1111-1111-111111111111', 1),
    ('c1111111-1111-1111-1111-111111111111', 'b2222222-2222-2222-2222-222222222222', 2),
    ('c2222222-2222-2222-2222-222222222222', 'b2222222-2222-2222-2222-222222222222', 1),
    ('c2222222-2222-2222-2222-222222222222', 'b3333333-3333-3333-3333-333333333333', 2)
ON CONFLICT DO NOTHING;

-- Add sample claims
INSERT INTO patents.claims (patent_id, claim_number, claim_text, claim_type, depends_on_claim) VALUES
    ('c1111111-1111-1111-1111-111111111111', 1,
     'A method for processing data comprising: receiving input data; processing the input data using a distributed system; and outputting processed data.',
     'independent', NULL),
    ('c1111111-1111-1111-1111-111111111111', 2,
     'The method of claim 1, wherein the distributed system comprises a plurality of compute nodes.',
     'dependent', 1),
    ('c2222222-2222-2222-2222-222222222222', 1,
     'A wireless communication device comprising: an antenna; a signal processor; and a controller configured to manage communications.',
     'independent', NULL)
ON CONFLICT DO NOTHING;

-- Add sample citations
INSERT INTO patents.patent_citations (citing_patent_id, cited_patent_id, citation_type) VALUES
    ('c1111111-1111-1111-1111-111111111111', 'c2222222-2222-2222-2222-222222222222', 'applicant')
ON CONFLICT DO NOTHING;
*/
