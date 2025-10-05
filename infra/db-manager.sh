#!/bin/bash
# Patent Discovery System - Database Management Script
# Provides easy commands for managing PostgreSQL and Neo4j databases

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_help() {
    cat << EOF
Patent Discovery System - Database Manager

Usage: ./db-manager.sh [command]

Commands:
  start           Start all database services
  stop            Stop all database services
  restart         Restart all database services
  status          Show status of all services
  logs            Show logs from all services
  logs-postgres   Show PostgreSQL logs
  logs-neo4j      Show Neo4j logs

  psql            Connect to PostgreSQL with psql
  cypher          Connect to Neo4j with cypher-shell

  init-postgres   Reinitialize PostgreSQL schema
  init-neo4j      Initialize Neo4j schema
  init-all        Initialize both databases

  backup          Backup both databases
  backup-postgres Backup PostgreSQL only
  backup-neo4j    Backup Neo4j only

  reset           Reset all databases (WARNING: deletes all data)
  reset-postgres  Reset PostgreSQL only (WARNING: deletes all data)
  reset-neo4j     Reset Neo4j only (WARNING: deletes all data)

  stats           Show database statistics
  health          Check health of all services

  help            Show this help message

Examples:
  ./db-manager.sh start
  ./db-manager.sh psql
  ./db-manager.sh backup
EOF
}

start_services() {
    echo -e "${GREEN}Starting database services...${NC}"
    docker-compose -f "$COMPOSE_FILE" up -d
    echo -e "${GREEN}Services started!${NC}"
    echo "PostgreSQL: localhost:5432"
    echo "Neo4j Browser: http://localhost:7474"
}

stop_services() {
    echo -e "${YELLOW}Stopping database services...${NC}"
    docker-compose -f "$COMPOSE_FILE" stop
    echo -e "${GREEN}Services stopped!${NC}"
}

restart_services() {
    echo -e "${YELLOW}Restarting database services...${NC}"
    docker-compose -f "$COMPOSE_FILE" restart
    echo -e "${GREEN}Services restarted!${NC}"
}

show_status() {
    docker-compose -f "$COMPOSE_FILE" ps
}

show_logs() {
    docker-compose -f "$COMPOSE_FILE" logs -f
}

show_logs_postgres() {
    docker-compose -f "$COMPOSE_FILE" logs -f postgres
}

show_logs_neo4j() {
    docker-compose -f "$COMPOSE_FILE" logs -f neo4j
}

connect_psql() {
    echo -e "${GREEN}Connecting to PostgreSQL...${NC}"
    docker exec -it patent-postgres psql -U patent_user -d patents
}

connect_cypher() {
    echo -e "${GREEN}Connecting to Neo4j...${NC}"
    docker exec -it patent-neo4j cypher-shell -u neo4j -p patent_password
}

init_postgres() {
    echo -e "${YELLOW}Reinitializing PostgreSQL schema...${NC}"
    docker exec -i patent-postgres psql -U patent_user -d patents < "$SCRIPT_DIR/init-scripts/postgres/01_init_schema.sql"
    echo -e "${GREEN}PostgreSQL schema initialized!${NC}"
}

init_neo4j() {
    echo -e "${YELLOW}Initializing Neo4j schema...${NC}"
    docker exec -i patent-neo4j cypher-shell -u neo4j -p patent_password < "$SCRIPT_DIR/init-scripts/neo4j/01_init_schema.cypher"
    echo -e "${GREEN}Neo4j schema initialized!${NC}"
}

init_all() {
    init_postgres
    init_neo4j
}

backup_postgres() {
    BACKUP_DIR="$SCRIPT_DIR/backups"
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/postgres_$(date +%Y%m%d_%H%M%S).sql"

    echo -e "${YELLOW}Backing up PostgreSQL to $BACKUP_FILE...${NC}"
    docker exec patent-postgres pg_dump -U patent_user patents > "$BACKUP_FILE"
    echo -e "${GREEN}PostgreSQL backup complete!${NC}"
    echo "Backup saved to: $BACKUP_FILE"
}

backup_neo4j() {
    BACKUP_DIR="$SCRIPT_DIR/backups"
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="neo4j_$(date +%Y%m%d_%H%M%S).dump"

    echo -e "${YELLOW}Backing up Neo4j...${NC}"
    echo -e "${YELLOW}Note: This requires Neo4j to be stopped first${NC}"

    read -p "Stop Neo4j for backup? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose -f "$COMPOSE_FILE" stop neo4j
        docker exec patent-neo4j neo4j-admin database dump neo4j --to-path=/backups
        docker cp "patent-neo4j:/backups/neo4j.dump" "$BACKUP_DIR/$BACKUP_FILE"
        docker-compose -f "$COMPOSE_FILE" start neo4j
        echo -e "${GREEN}Neo4j backup complete!${NC}"
        echo "Backup saved to: $BACKUP_DIR/$BACKUP_FILE"
    else
        echo -e "${YELLOW}Backup cancelled${NC}"
    fi
}

backup_all() {
    backup_postgres
    backup_neo4j
}

reset_postgres() {
    echo -e "${RED}WARNING: This will delete all PostgreSQL data!${NC}"
    read -p "Are you sure? (type 'yes' to confirm) " -r
    echo
    if [[ $REPLY == "yes" ]]; then
        docker-compose -f "$COMPOSE_FILE" stop postgres
        docker volume rm patent-discovery-system_postgres_data 2>/dev/null || true
        docker-compose -f "$COMPOSE_FILE" up -d postgres
        echo -e "${GREEN}PostgreSQL reset complete!${NC}"
    else
        echo -e "${YELLOW}Reset cancelled${NC}"
    fi
}

reset_neo4j() {
    echo -e "${RED}WARNING: This will delete all Neo4j data!${NC}"
    read -p "Are you sure? (type 'yes' to confirm) " -r
    echo
    if [[ $REPLY == "yes" ]]; then
        docker-compose -f "$COMPOSE_FILE" stop neo4j
        docker volume rm patent-discovery-system_neo4j_data 2>/dev/null || true
        docker volume rm patent-discovery-system_neo4j_logs 2>/dev/null || true
        docker-compose -f "$COMPOSE_FILE" up -d neo4j
        sleep 5
        init_neo4j
        echo -e "${GREEN}Neo4j reset complete!${NC}"
    else
        echo -e "${YELLOW}Reset cancelled${NC}"
    fi
}

reset_all() {
    echo -e "${RED}WARNING: This will delete ALL database data!${NC}"
    read -p "Are you sure? (type 'yes' to confirm) " -r
    echo
    if [[ $REPLY == "yes" ]]; then
        docker-compose -f "$COMPOSE_FILE" down -v
        docker-compose -f "$COMPOSE_FILE" up -d
        sleep 10
        init_neo4j
        echo -e "${GREEN}All databases reset complete!${NC}"
    else
        echo -e "${YELLOW}Reset cancelled${NC}"
    fi
}

show_stats() {
    echo -e "${GREEN}=== PostgreSQL Statistics ===${NC}"
    docker exec patent-postgres psql -U patent_user -d patents -c "
    SELECT
        schemaname,
        tablename,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
        (SELECT COUNT(*) FROM patents.patents WHERE schemaname||'.'||tablename = 'patents.patents') AS row_count
    FROM pg_tables
    WHERE schemaname = 'patents'
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
    "

    echo -e "\n${GREEN}=== Neo4j Statistics ===${NC}"
    docker exec patent-neo4j cypher-shell -u neo4j -p patent_password "
    MATCH (n)
    RETURN labels(n)[0] AS NodeType, count(*) AS Count
    ORDER BY Count DESC;
    " || echo "Neo4j may not be ready yet"
}

check_health() {
    echo -e "${GREEN}=== Health Check ===${NC}"

    echo -n "PostgreSQL: "
    if docker exec patent-postgres pg_isready -U patent_user > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
    else
        echo -e "${RED}✗ Not responding${NC}"
    fi

    echo -n "Neo4j: "
    if docker exec patent-neo4j cypher-shell -u neo4j -p patent_password "RETURN 1;" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
    else
        echo -e "${RED}✗ Not responding${NC}"
    fi
}

# Main command dispatcher
case "${1:-}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    logs-postgres)
        show_logs_postgres
        ;;
    logs-neo4j)
        show_logs_neo4j
        ;;
    psql)
        connect_psql
        ;;
    cypher)
        connect_cypher
        ;;
    init-postgres)
        init_postgres
        ;;
    init-neo4j)
        init_neo4j
        ;;
    init-all)
        init_all
        ;;
    backup)
        backup_all
        ;;
    backup-postgres)
        backup_postgres
        ;;
    backup-neo4j)
        backup_neo4j
        ;;
    reset)
        reset_all
        ;;
    reset-postgres)
        reset_postgres
        ;;
    reset-neo4j)
        reset_neo4j
        ;;
    stats)
        show_stats
        ;;
    health)
        check_health
        ;;
    help|--help|-h)
        print_help
        ;;
    *)
        echo -e "${RED}Unknown command: ${1:-}${NC}"
        echo ""
        print_help
        exit 1
        ;;
esac
