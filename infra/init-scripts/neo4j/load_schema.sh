#!/bin/bash
# Load Neo4j schema initialization script
# This script loads the Cypher schema file into Neo4j

set -e

NEO4J_HOST="${NEO4J_HOST:-localhost}"
NEO4J_PORT="${NEO4J_PORT:-7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-patent_password}"

echo "Loading Neo4j schema..."
echo "Host: $NEO4J_HOST:$NEO4J_PORT"

# Wait for Neo4j to be ready
echo "Waiting for Neo4j to be ready..."
until cypher-shell -a "bolt://$NEO4J_HOST:$NEO4J_PORT" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" "RETURN 1;" > /dev/null 2>&1; do
  echo "Neo4j is unavailable - sleeping"
  sleep 2
done

echo "Neo4j is ready!"

# Load the schema file
echo "Creating constraints and indexes..."
cat "$(dirname "$0")/01_init_schema.cypher" | cypher-shell -a "bolt://$NEO4J_HOST:$NEO4J_PORT" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD"

echo "Neo4j schema initialization complete!"
