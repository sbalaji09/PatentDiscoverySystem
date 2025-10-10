"""
MCP Server for Patent Discovery System
Provides tools for patent ingestion, search, and analysis.
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import data-pipeline modules
sys.path.insert(0, str(Path(__file__).parent.parent / "data-pipeline"))

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# Import our pipeline components
from ingestion import USPTOIngestionService, extract_keywords
from parser_service import PatentParserService
from postgres_loader import PostgresLoader, get_connection_string

# Initialize server
server = Server("patent-discovery-mcp-server")

# this includes all the tools that can be used for patent discovery
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="fetch_patents_by_idea",
            description="Fetch patents from USPTO based on a user's invention idea. Extracts keywords and searches patent abstracts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_idea": {
                        "type": "string",
                        "description": "Description of the invention idea (e.g., 'A mobile device with touchscreen for browsing')"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of patents to fetch (default: 100)",
                        "default": 100
                    }
                },
                "required": ["user_idea"]
            },
        ),
        types.Tool(
            name="ingest_and_store_patents",
            description="Complete pipeline: Fetch patents from USPTO, parse them, and store in database. This orchestrates the full ingestion process.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_idea": {
                        "type": "string",
                        "description": "Description of the invention idea to search for"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of patents to fetch and store (default: 100)",
                        "default": 100
                    }
                },
                "required": ["user_idea"]
            },
        ),
        types.Tool(
            name="fetch_patents_by_assignee",
            description="Fetch patents by company or organization name (assignee).",
            inputSchema={
                "type": "object",
                "properties": {
                    "assignee_name": {
                        "type": "string",
                        "description": "Name of the company/organization (e.g., 'Apple Inc', 'IBM')"
                    },
                    "start_year": {
                        "type": "integer",
                        "description": "Optional: Year to start search from (e.g., 2020)"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of patents to fetch (default: 100)",
                        "default": 100
                    }
                },
                "required": ["assignee_name"]
            },
        ),
        types.Tool(
            name="get_database_stats",
            description="Get statistics about the patent database (counts of patents, claims, citations).",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="extract_keywords_from_idea",
            description="Extract relevant keywords from a user's invention idea (useful for understanding what will be searched).",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_idea": {
                        "type": "string",
                        "description": "Description of the invention idea"
                    },
                    "max_keywords": {
                        "type": "integer",
                        "description": "Maximum keywords to extract (default: 10)",
                        "default": 10
                    }
                },
                "required": ["user_idea"]
            },
        ),
    ]

# each tool defined above references a separate function
# this function calls other already defined functions in /data-pipeline
@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:

    try:
        if name == "fetch_patents_by_idea":
            return await fetch_patents_by_idea_handler(arguments)

        elif name == "ingest_and_store_patents":
            return await ingest_and_store_patents_handler(arguments)

        elif name == "fetch_patents_by_assignee":
            return await fetch_patents_by_assignee_handler(arguments)

        elif name == "get_database_stats":
            return await get_database_stats_handler(arguments)

        elif name == "extract_keywords_from_idea":
            return await extract_keywords_handler(arguments)

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"Error executing tool '{name}': {str(e)}"
            )
        ]

# fetch patent ideas that are similar to a user's idea
async def fetch_patents_by_idea_handler(arguments: dict | None) -> list[types.TextContent]:
    if not arguments:
        raise ValueError("Missing arguments")

    user_idea = arguments.get("user_idea")
    if not user_idea:
        raise ValueError("user_idea is required")

    max_results = arguments.get("max_results", 100)

    ingestion = USPTOIngestionService()

    raw_patents = ingestion.fetch_by_user_idea(user_idea)

    raw_patents = raw_patents[:max_results]

    result_text = f"# Patent Search Results\n\n"
    result_text += f"**Search Query:** {user_idea}\n"
    result_text += f"**Keywords Extracted:** {extract_keywords(user_idea)}\n"
    result_text += f"**Patents Found:** {len(raw_patents)}\n\n"

    if raw_patents:
        result_text += "## Top Patents:\n\n"
        for i, patent in enumerate(raw_patents[:10], 1):
            patent_num = patent.get('patent_number', 'N/A')
            title = patent.get('patent_title', 'Untitled')
            abstract = patent.get('patent_abstract', 'No abstract')
            date = patent.get('patent_date', 'N/A')

            if len(abstract) > 200:
                abstract = abstract[:200] + "..."

            result_text += f"### {i}. {patent_num}\n"
            result_text += f"**Title:** {title}\n"
            result_text += f"**Date:** {date}\n"
            result_text += f"**Abstract:** {abstract}\n\n"

        if len(raw_patents) > 10:
            result_text += f"\n*({len(raw_patents) - 10} more patents found but not displayed)*\n"
    else:
        result_text += "\nNo patents found matching your idea.\n"

    return [
        types.TextContent(
            type="text",
            text=result_text
        )
    ]

# this function is the entire pipeline for data including ingesting the data, parsing it, and storing it in the db
async def ingest_and_store_patents_handler(arguments: dict | None) -> list[types.TextContent]:
    if not arguments:
        raise ValueError("Missing arguments")

    user_idea = arguments.get("user_idea")
    if not user_idea:
        raise ValueError("user_idea is required")

    max_results = arguments.get("max_results", 100)

    result_text = f"# Patent Ingestion Pipeline\n\n"
    result_text += f"**User Idea:** {user_idea}\n\n"

    # Step 1: Fetch patents from USPTO
    result_text += "## Step 1: Fetching from USPTO API\n"
    ingestion = USPTOIngestionService()
    raw_patents = ingestion.fetch_by_user_idea(user_idea)
    raw_patents = raw_patents[:max_results]
    result_text += f"✓ Fetched {len(raw_patents)} patents from USPTO\n\n"

    if not raw_patents:
        result_text += "⚠️ No patents found. Pipeline stopped.\n"
        return [types.TextContent(type="text", text=result_text)]

    # Step 2: Parse patents
    result_text += "## Step 2: Parsing Patent Data\n"
    parser = PatentParserService()
    patents, claims, citations = parser.parse_patents(raw_patents)
    result_text += f"✓ Parsed {len(patents)} patents\n"
    result_text += f"✓ Extracted {len(claims)} claims\n"
    result_text += f"✓ Extracted {len(citations)} citations\n\n"

    # Step 3: Store in database
    result_text += "## Step 3: Storing in PostgreSQL\n"
    connection_string = get_connection_string()
    loader = PostgresLoader(connection_string)

    try:
        load_result = loader.load_patents(patents, claims, citations)
        result_text += f"✓ Inserted {load_result['patents']} patents\n"
        result_text += f"✓ Inserted {load_result['claims']} claims\n"
        result_text += f"✓ Inserted {load_result['citations']} citations\n\n"

        # Get updated stats
        stats = loader.get_connection_stats()
        result_text += "## Database Statistics\n"
        result_text += f"- Total Patents: {stats.get('total_patents', 0)}\n"
        result_text += f"- Total Claims: {stats.get('total_claims', 0)}\n"
        result_text += f"- Total Citations: {stats.get('total_citations', 0)}\n\n"

        result_text += "✅ **Pipeline completed successfully!**\n"

    except Exception as e:
        result_text += f"❌ **Database Error:** {str(e)}\n"
        result_text += "\nPlease check database connection settings.\n"

    return [
        types.TextContent(
            type="text",
            text=result_text
        )
    ]

# fetch patents by assignee / company name
async def fetch_patents_by_assignee_handler(arguments: dict | None) -> list[types.TextContent]:
    if not arguments:
        raise ValueError("Missing arguments")

    assignee_name = arguments.get("assignee_name")
    if not assignee_name:
        raise ValueError("assignee_name is required")

    start_year = arguments.get("start_year")
    max_results = arguments.get("max_results", 100)

    # Initialize ingestion service
    ingestion = USPTOIngestionService()

    # Fetch patents
    raw_patents = ingestion.fetch_by_assignee(assignee_name, start_year)
    raw_patents = raw_patents[:max_results]

    # Format response
    result_text = f"# Patents by Assignee\n\n"
    result_text += f"**Assignee:** {assignee_name}\n"
    if start_year:
        result_text += f"**Since Year:** {start_year}\n"
    result_text += f"**Patents Found:** {len(raw_patents)}\n\n"

    if raw_patents:
        result_text += "## Patents:\n\n"
        for i, patent in enumerate(raw_patents[:20], 1):
            patent_num = patent.get('patent_number', 'N/A')
            title = patent.get('patent_title', 'Untitled')
            date = patent.get('patent_date', 'N/A')

            result_text += f"{i}. **{patent_num}** - {title} ({date})\n"

        if len(raw_patents) > 20:
            result_text += f"\n*({len(raw_patents) - 20} more patents not displayed)*\n"
    else:
        result_text += "\nNo patents found for this assignee.\n"

    return [
        types.TextContent(
            type="text",
            text=result_text
        )
    ]

# get database statistics
async def get_database_stats_handler(arguments: dict | None) -> list[types.TextContent]:

    connection_string = get_connection_string()
    loader = PostgresLoader(connection_string)

    try:
        stats = loader.get_connection_stats()

        result_text = "# Patent Database Statistics\n\n"
        result_text += f"**Total Patents:** {stats.get('total_patents', 0):,}\n"
        result_text += f"**Total Claims:** {stats.get('total_claims', 0):,}\n"
        result_text += f"**Total Citations:** {stats.get('total_citations', 0):,}\n\n"

        if stats.get('total_patents', 0) > 0:
            avg_claims = stats.get('total_claims', 0) / stats.get('total_patents', 1)
            result_text += f"**Average Claims per Patent:** {avg_claims:.1f}\n"

        result_text += f"\n*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"

    except Exception as e:
        result_text = f"# Database Statistics\n\n"
        result_text += f"❌ **Error:** Could not retrieve statistics\n"
        result_text += f"**Details:** {str(e)}\n\n"
        result_text += "Please check database connection settings.\n"

    return [
        types.TextContent(
            type="text",
            text=result_text
        )
    ]

# extract keywords from the user's idea to make querying easier
async def extract_keywords_handler(arguments: dict | None) -> list[types.TextContent]:
    """Extract keywords from user's idea."""
    if not arguments:
        raise ValueError("Missing arguments")

    user_idea = arguments.get("user_idea")
    if not user_idea:
        raise ValueError("user_idea is required")

    max_keywords = arguments.get("max_keywords", 10)

    # Extract keywords
    keywords = extract_keywords(user_idea, max_keywords)
    keywords_list = keywords.split()

    # Format response
    result_text = f"# Keyword Extraction\n\n"
    result_text += f"**Original Text:**\n{user_idea}\n\n"
    result_text += f"**Extracted Keywords ({len(keywords_list)}):**\n"
    for i, keyword in enumerate(keywords_list, 1):
        result_text += f"{i}. {keyword}\n"

    result_text += f"\n**Search Query:**\n{keywords}\n"

    return [
        types.TextContent(
            type="text",
            text=result_text
        )
    ]


async def main():
    """Run the MCP server using stdin/stdout streams."""
    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            print("MCP Server starting...", file=sys.stderr)
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="patent-discovery-server",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except asyncio.CancelledError:
        print("\nMCP Server shutting down gracefully...", file=sys.stderr)
    except Exception as e:
        print(f"Error in MCP Server: {str(e)}", file=sys.stderr)
        raise
    finally:
        print("MCP Server stopped.", file=sys.stderr)


def run_server():
    """Run the MCP server with proper signal handling."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nReceived shutdown signal. Exiting...", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run_server()
