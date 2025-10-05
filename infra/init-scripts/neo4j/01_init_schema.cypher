// Patent Discovery System - Neo4j Graph Schema
// Version: 1.0.0
// This script creates constraints, indexes, and the graph schema for patent citation network

// ============================================================================
// CONSTRAINTS
// ============================================================================

// Patent node constraints - ensure uniqueness
CREATE CONSTRAINT patent_number_unique IF NOT EXISTS
FOR (p:Patent) REQUIRE p.patent_number IS UNIQUE;

CREATE CONSTRAINT patent_id_unique IF NOT EXISTS
FOR (p:Patent) REQUIRE p.id IS UNIQUE;

// Inventor node constraints
CREATE CONSTRAINT inventor_id_unique IF NOT EXISTS
FOR (i:Inventor) REQUIRE i.id IS UNIQUE;

// Assignee node constraints
CREATE CONSTRAINT assignee_id_unique IF NOT EXISTS
FOR (a:Assignee) REQUIRE a.id IS UNIQUE;

// Technology cluster constraints
CREATE CONSTRAINT tech_cluster_id_unique IF NOT EXISTS
FOR (tc:TechCluster) REQUIRE tc.id IS UNIQUE;

// ============================================================================
// INDEXES
// ============================================================================

// Patent indexes for performance
CREATE INDEX patent_filing_date IF NOT EXISTS
FOR (p:Patent) ON (p.filing_date);

CREATE INDEX patent_grant_date IF NOT EXISTS
FOR (p:Patent) ON (p.grant_date);

CREATE INDEX patent_country IF NOT EXISTS
FOR (p:Patent) ON (p.country);

CREATE INDEX patent_status IF NOT EXISTS
FOR (p:Patent) ON (p.status);

// Full-text search indexes
CREATE FULLTEXT INDEX patent_text_search IF NOT EXISTS
FOR (p:Patent) ON EACH [p.title, p.abstract];

// Inventor indexes
CREATE INDEX inventor_name IF NOT EXISTS
FOR (i:Inventor) ON (i.normalized_name);

// Assignee indexes
CREATE INDEX assignee_name IF NOT EXISTS
FOR (a:Assignee) ON (a.normalized_name);

CREATE INDEX assignee_country IF NOT EXISTS
FOR (a:Assignee) ON (a.country);

// Technology cluster indexes
CREATE INDEX tech_cluster_code IF NOT EXISTS
FOR (tc:TechCluster) ON (tc.code);

// ============================================================================
// PROPERTY EXISTENCE CONSTRAINTS (Neo4j Enterprise only - commented out)
// ============================================================================

// CREATE CONSTRAINT patent_number_exists IF NOT EXISTS
// FOR (p:Patent) REQUIRE p.patent_number IS NOT NULL;

// CREATE CONSTRAINT patent_title_exists IF NOT EXISTS
// FOR (p:Patent) REQUIRE p.title IS NOT NULL;

// ============================================================================
// GRAPH SCHEMA DOCUMENTATION
// ============================================================================

// Node Types:
// -----------
// (:Patent)
//   Properties:
//     - id: UUID (from PostgreSQL, for sync)
//     - patent_number: String (unique identifier, e.g., "US-10123456-B2")
//     - title: String
//     - abstract: String
//     - filing_date: Date
//     - publication_date: Date
//     - grant_date: Date
//     - country: String (ISO 3166-1 alpha-3)
//     - patent_type: String
//     - status: String
//     - ipc_codes: [String]
//     - cpc_codes: [String]
//     - cited_by_count: Integer (denormalized)
//     - cites_count: Integer (denormalized)
//     - pagerank: Float (computed)
//     - betweenness: Float (computed)
//     - community_id: String (computed via graph algorithms)
//
// (:Inventor)
//   Properties:
//     - id: UUID
//     - full_name: String
//     - normalized_name: String
//     - country: String
//     - patent_count: Integer (denormalized)
//
// (:Assignee)
//   Properties:
//     - id: UUID
//     - name: String
//     - normalized_name: String
//     - organization_type: String
//     - country: String
//     - patent_count: Integer (denormalized)
//
// (:TechCluster)
//   Properties:
//     - id: String
//     - code: String (IPC/CPC code)
//     - classification_type: String (IPC or CPC)
//     - description: String
//     - level: Integer (hierarchy level)
//
// Relationship Types:
// -------------------
// (Patent)-[:CITES]->(Patent)
//   Properties:
//     - citation_type: String (examiner, applicant, third-party)
//     - created_at: DateTime
//
// (Patent)-[:INVENTED_BY]->(Inventor)
//   Properties:
//     - sequence: Integer (order of inventors)
//
// (Patent)-[:ASSIGNED_TO]->(Assignee)
//   Properties:
//     - sequence: Integer
//     - assignment_date: Date
//
// (Patent)-[:CLASSIFIED_AS]->(TechCluster)
//   Properties:
//     - primary: Boolean (is this the primary classification)
//
// (Inventor)-[:CO_INVENTOR]->(Inventor)
//   Properties:
//     - collaboration_count: Integer
//     - patents: [String] (list of patent numbers)
//
// (Assignee)-[:ACQUIRED|MERGED_WITH]->(Assignee)
//   Properties:
//     - date: Date
//     - type: String
//
// (TechCluster)-[:PARENT_OF]->(TechCluster)
//   Properties:
//     - hierarchy_level: Integer

// ============================================================================
// SAMPLE QUERIES (for reference)
// ============================================================================

// Find most cited patents in a technology area
// MATCH (p:Patent)-[:CLASSIFIED_AS]->(tc:TechCluster {code: 'H04L'})
// RETURN p.patent_number, p.title, p.cited_by_count
// ORDER BY p.cited_by_count DESC
// LIMIT 10;

// Find citation chain between two patents
// MATCH path = shortestPath(
//   (p1:Patent {patent_number: 'US-10000000-B2'})-[:CITES*]->(p2:Patent {patent_number: 'US-9000000-B2'})
// )
// RETURN path;

// Find co-inventors of a specific inventor
// MATCH (i1:Inventor {normalized_name: 'john_doe'})-[:CO_INVENTOR]-(i2:Inventor)
// RETURN i2.full_name, i2.patent_count
// ORDER BY i2.patent_count DESC;

// Find patents that cite multiple patents from a company
// MATCH (p:Patent)-[:CITES]->(cited:Patent)-[:ASSIGNED_TO]->(a:Assignee {normalized_name: 'apple_inc'})
// WITH p, COUNT(DISTINCT cited) as citation_count
// WHERE citation_count >= 3
// RETURN p.patent_number, p.title, citation_count
// ORDER BY citation_count DESC;

// Detect patent clusters using community detection (requires GDS library)
// CALL gds.graph.project(
//   'patent-citation-graph',
//   'Patent',
//   'CITES'
// );
// CALL gds.louvain.stream('patent-citation-graph')
// YIELD nodeId, communityId
// RETURN gds.util.asNode(nodeId).patent_number AS patent, communityId
// ORDER BY communityId;

// Calculate PageRank for patents (requires GDS library)
// CALL gds.pageRank.stream('patent-citation-graph')
// YIELD nodeId, score
// RETURN gds.util.asNode(nodeId).patent_number AS patent, score
// ORDER BY score DESC
// LIMIT 20;
