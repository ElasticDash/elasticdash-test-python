"""
Example tools configuration file for ElasticDash Test.
This file contains tool functions that can be called by AI agents.
"""

from typing import Dict, Any


def get_langfuse_overview() -> Dict[str, Any]:
    """
    Retrieves an overview of traces, scores, and observations from Langfuse.
    
    Returns:
        Dict containing counts and summaries of Langfuse data.
    """
    # This is a sample implementation
    return {
        "total_traces": 150,
        "total_observations": 847,
        "average_scores": {
            "quality": 0.85,
            "relevance": 0.92
        },
        "status": "success"
    }


def search_documentation(query: str, limit: int = 5) -> list:
    """
    Searches documentation based on a query string.
    
    Args:
        query: The search query
        limit: Maximum number of results to return
        
    Returns:
        List of matching documentation entries.
    """
    # Sample implementation
    return [
        {"title": "Getting Started", "url": "/docs/getting-started", "score": 0.95},
        {"title": "API Reference", "url": "/docs/api", "score": 0.87}
    ]


async def fetch_external_data(endpoint: str) -> Dict[str, Any]:
    """
    Asynchronously fetches data from an external API endpoint.
    
    Args:
        endpoint: The API endpoint to fetch from
        
    Returns:
        JSON response from the API.
    """
    # Sample async implementation
    return {"data": "sample", "endpoint": endpoint}
