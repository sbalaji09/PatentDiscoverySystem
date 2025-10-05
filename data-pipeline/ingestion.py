"""
USPTO Patent Data Ingestion
Responsible for: Fetching raw patent data from USPTO PatentsView API
"""

import os
import re
import logging
import requests
from typing import Dict, List, Optional, Set
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# extracts the keywords from the user query to be passed into the USPTO API to find relevant patents
def extract_keywords(user_idea: str, max_keywords: int = 10) -> str:

    text = user_idea.lower()


    text = re.sub(r'[^\w\s\-]', ' ', text)


    stopwords = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
        'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
        'to', 'was', 'will', 'with', 'would', 'could', 'should', 'can',
        'i', 'my', 'we', 'our', 'this', 'these', 'those', 'am', 'been',
        'have', 'had', 'do', 'does', 'did', 'but', 'if', 'or', 'because',
        'until', 'while', 'about', 'into', 'through', 'want', 'need'
    }

    
    words = text.split()

    
    keywords = [
        word for word in words
        if word not in stopwords and len(word) >= 3
    ]

    
    seen: Set[str] = set()
    unique_keywords = []
    for word in keywords:
        if word not in seen:
            seen.add(word)
            unique_keywords.append(word)

    
    result_keywords = unique_keywords[:max_keywords]

    logger.info(f"Extracted keywords: {result_keywords}")

    return ' '.join(result_keywords)


# this class fetches patent data from USPTO based on the user input while also handling paginating and rate limiting
class USPTOIngestionService:

    BASE_URL = "https://search.patentsview.org/api/v1/patent/"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('PATENTSVIEW_API_KEY')
        if not self.api_key:
            logger.warning("No API key provided. Set PATENTSVIEW_API_KEY environment variable.")

        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                'X-Api-Key': self.api_key,
                'Content-Type': 'application/json'
            })

    # fetch patents from USPTO API based on the query provided by the user
    def fetch_patents_by_query(self, query: Dict, fields: Optional[List[str]] = None,
                               per_page: int = 100, max_pages: int = 5) -> List[Dict]:
        if fields is None:
           
            fields = [
                'patent_number',
                'patent_title',
                'patent_abstract',
                'patent_date',
                'app_date',
                'assignees',
                'inventors',
                'claims',
                'cited_patents',
                'citedby_patents',
                'ipc_classes',
                'cpc_classes'
            ]

        
        payload = {
            'q': query,
            'f': fields,
            'o': {
                'per_page': per_page,
                'page': 1
            }
        }

        all_patents = []

        try:
            logger.info(f"Fetching patents with query: {json.dumps(query)}")

            # Make initial request
            response = self.session.post(
                self.BASE_URL,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()

            # Extract patents from response
            if 'patents' in data:
                patents = data['patents']
                all_patents.extend(patents)
                logger.info(f"Fetched {len(patents)} patents from page 1")

                
                total_count = data.get('count', len(patents))
                total_pages = data.get('total_pages', 1)

                logger.info(f"Total results: {total_count}, Total pages: {total_pages}")

                
                pages_to_fetch = min(max_pages, total_pages)
                for page in range(2, pages_to_fetch + 1):
                    payload['o']['page'] = page

                    response = self.session.post(
                        self.BASE_URL,
                        json=payload,
                        timeout=30
                    )
                    response.raise_for_status()

                    data = response.json()
                    if 'patents' in data:
                        all_patents.extend(data['patents'])
                        logger.info(f"Fetched page {page}, total patents: {len(all_patents)}")

            logger.info(f"Total patents fetched: {len(all_patents)}")
            return all_patents

        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            return []
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing API response: {e}")
            return []

    # fetches patents related to the user's invetion idea
    def fetch_by_user_idea(self, user_idea: str) -> List[Dict]:
        keywords = extract_keywords(user_idea)

        query = {
            "_text_any": {"patent_abstract": keywords}
        }

        return self.fetch_patents_by_query(query)

    # fetches additional patents in the specific technology area related to the user's invention idea
    def fetch_by_technology_area(self, ipc_code: str, year: int) -> List[Dict]:
        query = {
            "_and": [
                {"ipc_class": ipc_code},
                {"_gte": {"patent_date": f"{year}-01-01"}}
            ]
        }

        return self.fetch_patents_by_query(query)

    # fetches the patents based on their specific id numbers
    def fetch_by_patent_numbers(self, patent_numbers: List[str]) -> List[Dict]:
        query = {
            "_in": {"patent_number": patent_numbers}
        }

        return self.fetch_patents_by_query(query)

    # fetch patents by assignee organization
    def fetch_by_assignee(self, assignee_name: str, start_year: Optional[int] = None) -> List[Dict]:
        query = {
            "_contains": {"assignee_organization": assignee_name}
        }

        if start_year:
            query = {
                "_and": [
                    query,
                    {"_gte": {"patent_date": f"{start_year}-01-01"}}
                ]
            }

        return self.fetch_patents_by_query(query)


def main():
    #Example usage of USPTO ingestion service

    # Initialize ingestion service
    ingestion = USPTOIngestionService()

    # Example 1: Fetch by user idea
    user_idea = "A mobile device with a touchscreen interface for browsing the internet"
    logger.info(f"Fetching patents for user idea: {user_idea}")
    patents = ingestion.fetch_by_user_idea(user_idea)
    logger.info(f"Fetched {len(patents)} patents")

    # Example 2: Fetch by technology area
    # patents = ingestion.fetch_by_technology_area("H04L", 2023)

    # Example 3: Fetch by assignee
    # patents = ingestion.fetch_by_assignee("Apple Inc", 2020)

    # Next step: Pass raw patents to parser_service for extraction


if __name__ == "__main__":
    main()
