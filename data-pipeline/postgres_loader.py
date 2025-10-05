"""
PostgreSQL Loader
Responsible for: Inserting parsed patent data into PostgreSQL database
"""

import os
import logging
import psycopg2
from psycopg2.extras import execute_values, Json
from typing import List
from parser_service import ParsedPatent, ParsedClaim, ParsedCitation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# loads parsed patent data into postgresql database
class PostgresLoader:

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    # load patents, claims, and citations into database
    def load_patents(self, patents: List[ParsedPatent],
                    claims: List[ParsedClaim],
                    citations: List[ParsedCitation]) -> dict:
        if not patents:
            logger.info("No patents to load")
            return {'patents': 0, 'claims': 0, 'citations': 0}

        conn = None
        result = {'patents': 0, 'claims': 0, 'citations': 0}

        try:
            conn = psycopg2.connect(self.connection_string)
            cur = conn.cursor()

            # 1. Insert patents first (to maintain referential integrity)
            result['patents'] = self._insert_patents(cur, patents)
            conn.commit()

            # 2. Insert claims (requires patent_id from patents table)
            result['claims'] = self._insert_claims(cur, claims)
            conn.commit()

            # 3. Insert citations
            result['citations'] = self._insert_citations(cur, citations)
            conn.commit()

            logger.info(f"Successfully loaded: {result['patents']} patents, "
                       f"{result['claims']} claims, {result['citations']} citations")

        except psycopg2.Error as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

        return result

    # insert patents into patents table
    def _insert_patents(self, cur, patents: List[ParsedPatent]) -> int:
        inserted_count = 0

        for patent in patents:
            try:
                cur.execute("""
                    INSERT INTO patents.patents
                    (patent_number, title, abstract, filing_date, grant_date,
                     assignee_name, inventor_names, raw_data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (patent_number) DO UPDATE SET
                        title = EXCLUDED.title,
                        abstract = EXCLUDED.abstract,
                        filing_date = EXCLUDED.filing_date,
                        grant_date = EXCLUDED.grant_date,
                        assignee_name = EXCLUDED.assignee_name,
                        inventor_names = EXCLUDED.inventor_names,
                        raw_data = EXCLUDED.raw_data
                    RETURNING id
                """, (
                    patent.patent_number,
                    patent.title,
                    patent.abstract,
                    patent.filing_date,
                    patent.grant_date,
                    patent.assignee_name,
                    patent.inventor_names,
                    Json(patent.raw_data)
                ))

                inserted_count += 1

            except psycopg2.Error as e:
                logger.error(f"Error inserting patent {patent.patent_number}: {e}")
                raise

        logger.info(f"Inserted {inserted_count} patents")
        return inserted_count

    # insert claims into claims table
    def _insert_claims(self, cur, claims: List[ParsedClaim]) -> int:
        if not claims:
            return 0

        inserted_count = 0

        # Group claims by patent number for efficient processing
        claims_by_patent = {}
        for claim in claims:
            if claim.patent_number not in claims_by_patent:
                claims_by_patent[claim.patent_number] = []
            claims_by_patent[claim.patent_number].append(claim)

        # Insert claims for each patent
        for patent_number, patent_claims in claims_by_patent.items():
            try:
                # Get patent_id
                cur.execute(
                    "SELECT id FROM patents.patents WHERE patent_number = %s",
                    (patent_number,)
                )
                result = cur.fetchone()

                if not result:
                    logger.warning(f"Patent {patent_number} not found, skipping claims")
                    continue

                patent_id = result[0]

                # Delete existing claims for this patent (to handle updates)
                cur.execute(
                    "DELETE FROM patents.claims WHERE patent_id = %s",
                    (patent_id,)
                )

                # Prepare claims data for bulk insert
                claims_data = [
                    (patent_id, claim.claim_number, claim.claim_text)
                    for claim in patent_claims
                ]

                # Bulk insert claims
                execute_values(
                    cur,
                    """
                    INSERT INTO patents.claims (patent_id, claim_number, claim_text)
                    VALUES %s
                    """,
                    claims_data
                )

                inserted_count += len(claims_data)

            except psycopg2.Error as e:
                logger.error(f"Error inserting claims for patent {patent_number}: {e}")
                raise

        logger.info(f"Inserted {inserted_count} claims")
        return inserted_count

    # insert citations into citations table
    def _insert_citations(self, cur, citations: List[ParsedCitation]) -> int:
        if not citations:
            return 0

        inserted_count = 0

        # Prepare citations data for bulk insert
        citations_data = [
            (citation.citing_patent, citation.cited_patent, citation.citation_type)
            for citation in citations
        ]

        try:
            # Bulk insert with ON CONFLICT to handle duplicates
            for citing, cited, ctype in citations_data:
                cur.execute("""
                    INSERT INTO patents.citations
                    (citing_patent_number, cited_patent_number, citation_type)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (citing_patent_number, cited_patent_number) DO NOTHING
                """, (citing, cited, ctype))

                if cur.rowcount > 0:
                    inserted_count += 1

            logger.info(f"Inserted {inserted_count} citations")

        except psycopg2.Error as e:
            logger.error(f"Error inserting citations: {e}")
            raise

        return inserted_count

    # gets the database connection statistics to prevent any errors
    def get_connection_stats(self) -> dict:
        conn = None
        stats = {}

        try:
            conn = psycopg2.connect(self.connection_string)
            cur = conn.cursor()

            # Count patents
            cur.execute("SELECT COUNT(*) FROM patents.patents")
            stats['total_patents'] = cur.fetchone()[0]

            # Count claims
            cur.execute("SELECT COUNT(*) FROM patents.claims")
            stats['total_claims'] = cur.fetchone()[0]

            # Count citations
            cur.execute("SELECT COUNT(*) FROM patents.citations")
            stats['total_citations'] = cur.fetchone()[0]

        except psycopg2.Error as e:
            logger.error(f"Error getting stats: {e}")
        finally:
            if conn:
                conn.close()

        return stats

# build the postgres connection string from environment variables in .env
def get_connection_string() -> str:
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'patent_discovery')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', 'postgres')

    return f"host={db_host} port={db_port} dbname={db_name} user={db_user} password={db_password}"


def main():
    """Example usage of PostgreSQL loader."""

    # Example parsed data
    from parser_service import ParsedPatent, ParsedClaim, ParsedCitation
    from datetime import date

    patents = [
        ParsedPatent(
            patent_number='10000000',
            title='Example Patent',
            abstract='This is an example abstract.',
            filing_date=date(2018, 6, 20),
            grant_date=date(2020, 1, 15),
            assignee_name='Example Corp',
            inventor_names='John Doe',
            raw_data={'example': 'data'}
        )
    ]

    claims = [
        ParsedClaim(
            patent_number='10000000',
            claim_number=1,
            claim_text='A method comprising...'
        ),
        ParsedClaim(
            patent_number='10000000',
            claim_number=2,
            claim_text='The method of claim 1...'
        )
    ]

    citations = [
        ParsedCitation(
            citing_patent='10000000',
            cited_patent='9999999',
            citation_type='backward'
        )
    ]

    # Initialize loader
    connection_string = get_connection_string()
    loader = PostgresLoader(connection_string)

    # Load data
    result = loader.load_patents(patents, claims, citations)
    logger.info(f"Load result: {result}")

    # Get stats
    stats = loader.get_connection_stats()
    logger.info(f"Database stats: {stats}")


if __name__ == "__main__":
    main()
