# Patent Discovery System - Infrastructure

This directory contains the infrastructure setup for the Patent Discovery System, including Docker Compose configuration and database initialization scripts.

## Quick Start

### Start Services

```bash
# Start all services
docker-compose -f infra/docker-compose.yml up -d

# Check service status
docker-compose -f infra/docker-compose.yml ps

# View logs
docker-compose -f infra/docker-compose.yml logs -f
```

### Stop Services

```bash
docker-compose -f infra/docker-compose.yml down

# Stop and remove volumes (WARNING: This will delete all data)
docker-compose -f infra/docker-compose.yml down -v
```

## Services

### PostgreSQL
- **Port**: 5432
- **Database**: `patents`
- **User**: `patent_user`
- **Password**: `patent_password`
- **Connection String**: `postgresql://patent_user:patent_password@localhost:5432/patents`

### Neo4j
- **HTTP Port**: 7474 (Browser interface)
- **Bolt Port**: 7687 (Database connection)
- **User**: `neo4j`
- **Password**: `patent_password`
- **Browser URL**: http://localhost:7474
- **Connection URI**: `bolt://localhost:7687`

## Database Schemas

### PostgreSQL Schema

The PostgreSQL database uses a relational schema optimized for storing detailed patent metadata:

#### Tables

**`patents.patents`** - Main patent metadata
- `id` (UUID, PK)
- `patent_number` (VARCHAR, unique) - e.g., "US-10123456-B2"
- `title`, `abstract`, `description` (TEXT)
- `filing_date`, `publication_date`, `grant_date` (DATE)
- `country`, `patent_type`, `status` (VARCHAR)
- `ipc_codes`, `cpc_codes`, `uspc_codes` (TEXT[])
- `cited_by_count`, `cites_count` (INTEGER, denormalized)

**`patents.claims`** - Individual patent claims
- `id` (UUID, PK)
- `patent_id` (UUID, FK → patents)
- `claim_number` (INTEGER)
- `claim_text` (TEXT)
- `claim_type` (VARCHAR) - 'independent' or 'dependent'
- `depends_on_claim` (INTEGER, nullable)

**`patents.inventors`** - Deduplicated inventors
- `id` (UUID, PK)
- `first_name`, `last_name`, `full_name` (VARCHAR)
- `normalized_name` (VARCHAR, unique)
- `country`, `city` (VARCHAR)

**`patents.assignees`** - Deduplicated assignees/owners
- `id` (UUID, PK)
- `name`, `normalized_name` (VARCHAR)
- `organization_type` (VARCHAR) - company, university, individual, etc.
- `country`, `address` (VARCHAR/TEXT)

**`patents.patent_inventors`** - Many-to-many junction table
- `patent_id`, `inventor_id` (UUIDs, composite PK)
- `sequence` (INTEGER) - Order of inventors

**`patents.patent_assignees`** - Many-to-many junction table
- `patent_id`, `assignee_id` (UUIDs, composite PK)
- `sequence` (INTEGER)
- `assignment_date` (DATE)

**`patents.patent_citations`** - Citation relationships
- `citing_patent_id`, `cited_patent_id` (UUIDs, composite PK)
- `citation_type` (VARCHAR) - examiner, applicant, third-party

#### Views

**`patents.patents_complete`** - Denormalized view with inventors and assignees arrays

#### Features

- Full-text search indexes using `pg_trgm` extension
- Automatic timestamp updates via triggers
- Citation count denormalization for performance
- Constraint validation for data integrity
- GIN indexes for array fields (classification codes)

### Neo4j Graph Schema

The Neo4j database stores the patent citation network for graph analysis:

#### Node Types

**`(:Patent)`** - Patent nodes
- `id` (UUID, synced with PostgreSQL)
- `patent_number` (STRING, unique)
- `title`, `abstract` (STRING)
- `filing_date`, `grant_date` (DATE)
- `country`, `status` (STRING)
- `ipc_codes`, `cpc_codes` (LIST)
- `cited_by_count`, `cites_count` (INTEGER)
- `pagerank`, `betweenness`, `community_id` (computed metrics)

**`(:Inventor)`** - Inventor nodes
- `id`, `full_name`, `normalized_name` (STRING)
- `country` (STRING)
- `patent_count` (INTEGER)

**`(:Assignee)`** - Assignee/owner nodes
- `id`, `name`, `normalized_name` (STRING)
- `organization_type`, `country` (STRING)
- `patent_count` (INTEGER)

**`(:TechCluster)`** - Technology classification nodes
- `id`, `code` (STRING) - IPC/CPC codes
- `classification_type` (STRING) - 'IPC' or 'CPC'
- `description`, `level` (STRING/INTEGER)

#### Relationship Types

- `(Patent)-[:CITES {citation_type}]->(Patent)` - Citation relationships
- `(Patent)-[:INVENTED_BY {sequence}]->(Inventor)` - Inventor relationships
- `(Patent)-[:ASSIGNED_TO {sequence, assignment_date}]->(Assignee)` - Ownership
- `(Patent)-[:CLASSIFIED_AS {primary}]->(TechCluster)` - Technology classification
- `(Inventor)-[:CO_INVENTOR {collaboration_count, patents}]->(Inventor)` - Collaborations
- `(Assignee)-[:ACQUIRED|MERGED_WITH {date}]->(Assignee)` - Corporate events
- `(TechCluster)-[:PARENT_OF]->(TechCluster)` - Classification hierarchy

#### Features

- Uniqueness constraints on key properties
- Full-text search indexes on patent text
- Optimized for citation network analysis
- Support for graph algorithms (PageRank, community detection, centrality)
- APOC and Graph Data Science plugins enabled

## Initialization Scripts

### PostgreSQL

Located in `init-scripts/postgres/`:

1. **`01_init_schema.sql`** - Creates schema, tables, indexes, triggers, views
2. **`02_seed_data.sql`** - Sample seed data (commented out by default)

Scripts run automatically on first container startup via Docker entrypoint.

### Neo4j

Located in `init-scripts/neo4j/`:

1. **`01_init_schema.cypher`** - Creates constraints, indexes, and schema documentation
2. **`load_schema.sh`** - Helper script to load the schema

To manually load Neo4j schema:

```bash
# From inside Neo4j container
docker exec -it patent-neo4j bash
cd /var/lib/neo4j/import
./load_schema.sh

# Or from host (if schema is mounted)
cd infra/init-scripts/neo4j
./load_schema.sh
```

Or using cypher-shell directly:

```bash
docker exec -it patent-neo4j cypher-shell -u neo4j -p patent_password < init-scripts/neo4j/01_init_schema.cypher
```

## Data Synchronization

The system uses both PostgreSQL and Neo4j:
- **PostgreSQL**: Source of truth for all patent data, metadata, and full-text
- **Neo4j**: Optimized for citation network analysis and graph queries

Data should be synced from PostgreSQL → Neo4j using ETL pipelines (to be implemented).

## Common Operations

### Connect to PostgreSQL

```bash
# Using psql from host (requires psql client)
psql postgresql://patent_user:patent_password@localhost:5432/patents

# Using Docker
docker exec -it patent-postgres psql -U patent_user -d patents
```

### Connect to Neo4j

```bash
# Using cypher-shell from Docker
docker exec -it patent-neo4j cypher-shell -u neo4j -p patent_password

# Or open browser
open http://localhost:7474
```

### Backup Data

```bash
# PostgreSQL backup
docker exec patent-postgres pg_dump -U patent_user patents > backup_$(date +%Y%m%d).sql

# Neo4j backup (stop Neo4j first)
docker exec patent-neo4j neo4j-admin database dump neo4j --to-path=/backups
```

### Restore Data

```bash
# PostgreSQL restore
docker exec -i patent-postgres psql -U patent_user -d patents < backup_20250101.sql

# Neo4j restore
docker exec patent-neo4j neo4j-admin database load neo4j --from-path=/backups
```

## Monitoring

### Health Checks

```bash
# Check PostgreSQL health
docker exec patent-postgres pg_isready -U patent_user

# Check Neo4j health
docker exec patent-neo4j cypher-shell -u neo4j -p patent_password 'RETURN 1;'
```

### View Database Stats

```bash
# PostgreSQL - table sizes
docker exec -it patent-postgres psql -U patent_user -d patents -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'patents'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# Neo4j - node/relationship counts
docker exec patent-neo4j cypher-shell -u neo4j -p patent_password "
MATCH (n)
RETURN labels(n) AS NodeType, count(*) AS Count
ORDER BY Count DESC;
"
```

## Troubleshooting

### PostgreSQL issues

```bash
# View logs
docker logs patent-postgres

# Check connections
docker exec patent-postgres psql -U patent_user -d patents -c "SELECT count(*) FROM pg_stat_activity;"
```

### Neo4j issues

```bash
# View logs
docker logs patent-neo4j

# Check if APOC is loaded
docker exec patent-neo4j cypher-shell -u neo4j -p patent_password "CALL apoc.help('all');"
```

### Reset everything

```bash
# WARNING: This deletes all data
docker-compose -f infra/docker-compose.yml down -v
docker-compose -f infra/docker-compose.yml up -d
```

## Development Notes

- Default credentials are for development only. Change for production!
- PostgreSQL uses UTC timezone
- Neo4j community edition has some limitations (no role-based access control)
- Consider increasing Neo4j heap size for large datasets
- Enable PostgreSQL query logging for development: `log_statement = 'all'`
