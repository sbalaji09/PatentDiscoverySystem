from flask import Flask, jsonify, request
from flask_restful import Resource, Api
import sys
from pathlib import Path

# Add data-pipeline to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "data-pipeline"))
from postgres_loader import get_connection_string
from ingestion import USPTOIngestionService
from parser_service import PatentParserService
from postgres_loader import PostgresLoader
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
api = Api(app)

# Endpoint 1: GET /api/patents - List patents with search/filter
class PatentsList(Resource):
    def get(self):
        search = request.args.get('search', '').lower()

        conn = None
        try:
            conn = psycopg2.connect(get_connection_string())
            cur = conn.cursor(cursor_factory=RealDictCursor)

            if search:
                cur.execute("""
                    SELECT patent_number, title, abstract, grant_date, assignee_name
                    FROM patents.patents
                    WHERE LOWER(title) LIKE %s OR LOWER(abstract) LIKE %s
                    ORDER BY grant_date DESC
                    LIMIT 100
                """, (f'%{search}%', f'%{search}%'))
            else:
                cur.execute("""
                    SELECT patent_number, title, abstract, grant_date, assignee_name
                    FROM patents.patents
                    ORDER BY grant_date DESC
                    LIMIT 100
                """)

            patents = cur.fetchall()
            return jsonify([dict(p) for p in patents])

        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            if conn:
                conn.close()

# Endpoint 2: GET /api/patents/<patent_number> - Patent details
class PatentDetail(Resource):
    def get(self, patent_number):
        conn = None
        try:
            conn = psycopg2.connect(get_connection_string())
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                SELECT patent_number, title, abstract, filing_date, grant_date,
                       assignee_name, inventor_names, raw_data
                FROM patents.patents
                WHERE patent_number = %s
            """, (patent_number,))

            patent = cur.fetchone()
            if not patent:
                return jsonify({'error': 'Patent not found'}), 404

            patent_dict = dict(patent)

            cur.execute("""
                SELECT claim_number, claim_text
                FROM patents.claims c
                JOIN patents.patents p ON c.patent_id = p.id
                WHERE p.patent_number = %s
                ORDER BY claim_number
            """, (patent_number,))
            patent_dict['claims'] = [dict(c) for c in cur.fetchall()]

            cur.execute("""
                SELECT cited_patent_number
                FROM patents.citations
                WHERE citing_patent_number = %s AND citation_type = 'backward'
            """, (patent_number,))
            patent_dict['cited_patents'] = [c['cited_patent_number'] for c in cur.fetchall()]

            cur.execute("""
                SELECT citing_patent_number
                FROM patents.citations
                WHERE cited_patent_number = %s AND citation_type = 'forward'
            """, (patent_number,))
            patent_dict['citing_patents'] = [c['citing_patent_number'] for c in cur.fetchall()]

            return jsonify(patent_dict)

        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            if conn:
                conn.close()

# Endpoint 3: POST /api/search - Search by user idea (fetches from USPTO)
class PatentSearch(Resource):
    def post(self):
        data = request.get_json()
        if not data or 'user_idea' not in data:
            return jsonify({'error': 'user_idea is required'}), 400

        user_idea = data['user_idea']
        store_results = data.get('store', False)  # Optional: whether to store in DB

        try:
            ingestion = USPTOIngestionService()
            raw_patents = ingestion.fetch_by_user_idea(user_idea)

            if not raw_patents:
                return jsonify({
                    'message': 'No patents found',
                    'user_idea': user_idea,
                    'patents': []
                })

            parser = PatentParserService()
            patents, claims, citations = parser.parse_patents(raw_patents)

            if store_results:
                loader = PostgresLoader(get_connection_string())
                load_result = loader.load_patents(patents, claims, citations)
                stored_count = load_result['patents']
            else:
                stored_count = 0

            patent_list = [{
                'patent_number': p.patent_number,
                'title': p.title,
                'abstract': p.abstract,
                'grant_date': p.grant_date.isoformat() if p.grant_date else None,
                'assignee_name': p.assignee_name
            } for p in patents]

            return jsonify({
                'user_idea': user_idea,
                'patents_found': len(patent_list),
                'patents_stored': stored_count,
                'patents': patent_list
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

# Endpoint 4: GET /api/stats - Database statistics
class DatabaseStats(Resource):
    def get(self):
        conn = None
        try:
            conn = psycopg2.connect(get_connection_string())
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("SELECT COUNT(*) as count FROM patents.patents")
            total_patents = cur.fetchone()['count']

            cur.execute("SELECT COUNT(*) as count FROM patents.claims")
            total_claims = cur.fetchone()['count']

            cur.execute("SELECT COUNT(*) as count FROM patents.citations")
            total_citations = cur.fetchone()['count']

            cur.execute("""
                SELECT COUNT(*) as count
                FROM patents.patents
                WHERE grant_date >= CURRENT_DATE - INTERVAL '1 year'
            """)
            recent_patents = cur.fetchone()['count']

            cur.execute("""
                SELECT assignee_name, COUNT(*) as patent_count
                FROM patents.patents
                WHERE assignee_name IS NOT NULL
                GROUP BY assignee_name
                ORDER BY patent_count DESC
                LIMIT 10
            """)
            top_assignees = [dict(a) for a in cur.fetchall()]

            return jsonify({
                'total_patents': total_patents,
                'total_claims': total_claims,
                'total_citations': total_citations,
                'recent_patents_1year': recent_patents,
                'average_claims_per_patent': round(total_claims / total_patents, 1) if total_patents > 0 else 0,
                'top_assignees': top_assignees
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            if conn:
                conn.close()

# Register endpoints
api.add_resource(PatentsList, '/api/patents')
api.add_resource(PatentDetail, '/api/patents/<string:patent_number>')
api.add_resource(PatentSearch, '/api/search')
api.add_resource(DatabaseStats, '/api/stats')

if __name__ == '__main__':
    app.run(debug=True, port=5000)