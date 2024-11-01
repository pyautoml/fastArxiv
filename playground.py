"""
Example usage and testing playground for arXiv API client.

This module demonstrates the core functionality of the arXiv client including:
- Downloading papers locally
- Reading papers asynchronously
- Performance profiling
- Different query examples

Functions:
    download_locally: Download papers to local storage
    show: Display papers content in console"""

import asyncio
from papers import Arxiv, Query
from pyinstrument import Profiler
from typing import List, Optional


def download_locally(arxiv: Arxiv, queries: List[Query]) -> None:
    arxiv.download_papers(queries=queries, overwrite=False)

async def show(arxiv: Arxiv, queries: List[Query], prettify: Optional[bool] = True) -> None:
    async for paper in arxiv.read_papers(queries=queries, prettify=prettify):
        print(paper, end="\n\n")

async def main():

    profiler = Profiler()
    arxiv = Arxiv(logger=True, log_level="DEBUG", max_workers=100)
    queries=[
                Query(search_query="RAG", max_results=2),
                # Query(search_query="Agennts LLM", max_results=2),
                # Query(search_query="LangGraph", max_results=2)
    ]
    profiler.start()
    # download_locally(arxiv=arxiv, queries=queries)  # <-- uncomment / comment
    await show(arxiv=arxiv, queries=queries, prettify=True)  # <-- uncomment / comment
    profiler.stop()
    profiler.print()

if __name__ == "__main__":
    asyncio.run(main())
