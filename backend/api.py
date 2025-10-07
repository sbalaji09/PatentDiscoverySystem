from flask import Flask, jsonify, request
from flask_restful import Resource, Api
import sys
from pathlib import Path

# Add data-pipeline to path to import postgres_loader
sys.path.insert(0, str(Path(__file__).parent.parent / "data-pipeline"))
from postgres_loader import get_connection_string
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
api = Api(app)

class PatentsList(Resource):
    def get(self):
        # Example of simple search on title via query parameter
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