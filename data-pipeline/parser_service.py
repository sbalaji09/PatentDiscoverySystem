"""
Patent Parser Service
Responsible for: Extracting and structuring patent data, claims, and citations
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# data structure for the parsed patent
@dataclass
class ParsedPatent:
    patent_number: str
    title: str
    abstract: Optional[str]
    filing_date: Optional[date]
    grant_date: Optional[date]
    assignee_name: Optional[str]
    inventor_names: Optional[str]
    raw_data: Dict[str, Any]

# data structure for the parsed claim
@dataclass
class ParsedClaim:
    patent_number: str
    claim_number: int
    claim_text: str

# data structure for the parsed citation
@dataclass
class ParsedCitation:
    citing_patent: str
    cited_patent: str
    citation_type: str  # 'forward' or 'backward'

# parses raw patent data from USPTO API into structured objects
class PatentParserService:

    # parse raw patent data into structured objects
    def parse_patents(self, raw_patents: List[Dict]) -> tuple[List[ParsedPatent], List[ParsedClaim], List[ParsedCitation]]:
        patents = []
        claims = []
        citations = []

        for raw_patent in raw_patents:
            try:
                
                patent = self._parse_patent_metadata(raw_patent)
                if patent:
                    patents.append(patent)

                    
                    patent_claims = self._parse_claims(raw_patent)
                    claims.extend(patent_claims)

                    
                    patent_citations = self._parse_citations(raw_patent)
                    citations.extend(patent_citations)

            except Exception as e:
                patent_num = raw_patent.get('patent_number', 'unknown')
                logger.error(f"Error parsing patent {patent_num}: {e}")
                continue

        logger.info(f"Parsed {len(patents)} patents, {len(claims)} claims, {len(citations)} citations")

        return patents, claims, citations

    # extract patent metadata from raw API response
    def _parse_patent_metadata(self, raw_patent: Dict) -> Optional[ParsedPatent]:
        patent_number = raw_patent.get('patent_number')
        if not patent_number:
            logger.warning("Patent without number, skipping")
            return None

        title = raw_patent.get('patent_title', 'Untitled')

        abstract = raw_patent.get('patent_abstract')

        grant_date = self._parse_date(raw_patent.get('patent_date'))
        filing_date = self._parse_date(raw_patent.get('app_date'))

        assignees = raw_patent.get('assignees', [])
        assignee_name = None
        if assignees and len(assignees) > 0:
            assignee_name = assignees[0].get('assignee_organization')
            # Fallback to individual name if no organization
            if not assignee_name:
                first_name = assignees[0].get('assignee_first_name', '')
                last_name = assignees[0].get('assignee_last_name', '')
                assignee_name = f"{first_name} {last_name}".strip() or None

        inventors = raw_patent.get('inventors', [])
        inventor_names = ', '.join([
            f"{inv.get('inventor_name_first', '')} {inv.get('inventor_name_last', '')}".strip()
            for inv in inventors
            if inv.get('inventor_name_first') or inv.get('inventor_name_last')
        ]) if inventors else None

        raw_data = raw_patent

        return ParsedPatent(
            patent_number=patent_number,
            title=title,
            abstract=abstract,
            filing_date=filing_date,
            grant_date=grant_date,
            assignee_name=assignee_name,
            inventor_names=inventor_names,
            raw_data=raw_data
        )

    # extract claims from raw patent data
    def _parse_claims(self, raw_patent: Dict) -> List[ParsedClaim]:
        patent_number = raw_patent.get('patent_number')
        if not patent_number:
            return []

        claims = []
        raw_claims = raw_patent.get('claims', [])

        for idx, claim in enumerate(raw_claims, 1):
            claim_text = claim.get('claim_text')
            if claim_text:
                # Get explicit claim number if available, otherwise use index
                claim_number = claim.get('claim_number', idx)

                claims.append(ParsedClaim(
                    patent_number=patent_number,
                    claim_number=claim_number,
                    claim_text=claim_text.strip()
                ))

        return claims

    # extract citations from raw patent data
    def _parse_citations(self, raw_patent: Dict) -> List[ParsedCitation]:
        patent_number = raw_patent.get('patent_number')
        if not patent_number:
            return []

        citations = []

        # Backward citations (patents this patent cites)
        cited_patents = raw_patent.get('cited_patents', [])
        for cited in cited_patents:
            cited_patent_num = cited.get('cited_patent_number')
            if cited_patent_num:
                citations.append(ParsedCitation(
                    citing_patent=patent_number,
                    cited_patent=cited_patent_num,
                    citation_type='backward'
                ))

        # Forward citations (patents that cite this patent)
        citedby_patents = raw_patent.get('citedby_patents', [])
        for citedby in citedby_patents:
            citing_patent_num = citedby.get('citedby_patent_number')
            if citing_patent_num:
                citations.append(ParsedCitation(
                    citing_patent=citing_patent_num,
                    cited_patent=patent_number,
                    citation_type='forward'
                ))

        return citations

    # parse date string to date object
    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[date]:
        if not date_str:
            return None

        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            # Try alternative formats
            try:
                return datetime.strptime(date_str, '%Y%m%d').date()
            except ValueError:
                logger.warning(f"Could not parse date: {date_str}")
                return None


def main():
    """Example usage of parser service."""

    # Example raw patent data (as returned from USPTO API)
    raw_patents = [
        {
            'patent_number': '10000000',
            'patent_title': 'Example Patent',
            'patent_abstract': 'This is an example abstract.',
            'patent_date': '2020-01-15',
            'app_date': '2018-06-20',
            'assignees': [
                {'assignee_organization': 'Example Corp'}
            ],
            'inventors': [
                {'inventor_name_first': 'John', 'inventor_name_last': 'Doe'}
            ],
            'claims': [
                {'claim_number': 1, 'claim_text': 'A method comprising...'},
                {'claim_number': 2, 'claim_text': 'The method of claim 1...'}
            ],
            'cited_patents': [
                {'cited_patent_number': '9999999'}
            ],
            'citedby_patents': [
                {'citedby_patent_number': '10000001'}
            ]
        }
    ]

    # Initialize parser
    parser = PatentParserService()

    # Parse patents
    patents, claims, citations = parser.parse_patents(raw_patents)

    logger.info(f"Parsed {len(patents)} patents")
    logger.info(f"Extracted {len(claims)} claims")
    logger.info(f"Extracted {len(citations)} citations")

    # Next step: Pass parsed data to postgres_loader for insertion


if __name__ == "__main__":
    main()
