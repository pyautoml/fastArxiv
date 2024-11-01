"""
arXiv API client for searching and downloading academic papers.

This module provides a client for interacting with the arXiv API to search, download,
and process academic papers. 

Features include:
- Concurrent paper downloads using thread pools
- Configurable logging
- PDF content extraction
- Metadata parsing and cleaning
- File management for downloaded papers
- Rate limiting and error handling

Example:
    >>> from papers import Arxiv
    >>> client = Arxiv(logger=True)
    >>> client.get_papers([
    ...     Query(search_query="machine learning", max_results=5)
    ... ])

Dependencies:
    - httpx: For HTTP requests
    - concurrent.futures: For concurrent downloads
    - custom_logger: For logging configuration
    - utils: For helper functions

Author: [https://github.com/pyautoml]
License: MIT
Version: 1.0.0
"""

import os
import json
import httpx
import logging
from paper_builer import Query
from concurrent.futures import wait
from custom_exceptions import PaperGeneralError
from concurrent.futures import ThreadPoolExecutor
from custom_logger import setup_logger, null_logger
from typing import Any, AsyncGenerator, Dict, Final, Optional, List

from utils import (
    clean_text,
    check_path,
    xml_to_dict,
    save_to_file,
    extract_links,
    load_pdf_text,
    extract_authors,
    extract_category,
    extract_primary_category,
)

logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)

DEFAULT_MAX_WORKERS: int = 10
DEFAULT_BASE_URL: str = "http://export.arxiv.org/api/query?"


class Arxiv:
    """
    Client for interacting with the arXiv API.
    Provides methods for searching, downloading and processing arXiv papers.
    Handles concurrent downloads, logging, and file management.

    :ivar client: (httpx.Client) HTTP client for API requests.
    :ivar base_url: (str) Base URL for arXiv API.
    :ivar download_path: (str) Path for saving downloaded papers.
    :ivar logger (bool | logging.Logger): Logger instance for tracking operations.
    :ivar executor: Thread pool for concurrent operations.
    """

    def __init__(
        self,
        log_level: Optional[str] = "info",
        base_url: Optional[str] = DEFAULT_BASE_URL,
        logger: Optional[bool | logging.Logger] = False,
        max_workers: Optional[int] = DEFAULT_MAX_WORKERS,
        download_path: Optional[str] = check_path("ArxivPapers"),
    ):
        """
        Initialize Arxiv client.

        :param log_level: Logging level (debug, info, warning, error, critical)
        :param base_url: arXiv API base URL
        :param logger: Custom logger, True for default logger, or False for null logger
        :param max_workers: Maximum number of concurrent download threads
        :param download_path: Directory path for saving downloaded papers
        :raises OSError: If download path creation fails
        """
        self.client = httpx.Client()
        self.base_url: Final[str] = base_url
        self.download_path = check_path(download_path)
        self.log_level = (log_level,)
        self.logger = self.__setup_logger(logger, log_level)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def __setup_logger(
        self, logger: Optional[bool | logging.Logger], log_level: str
    ) -> logging.Logger:
        """
        Set up logging configuration.

        :param logger: (bool flag, or None) Logger instance.
        :param log_level: (str) Desired logging level.
        :returns Logger: Configured logger instance.
        """
        if not logger:
            return null_logger()
        if isinstance(logger, bool):
            return setup_logger(name=os.path.basename(__file__), log_level=log_level)
        return logger

    def extract_pdf_link(self, links: list) -> Optional[str]:
        """
        Extract PDF download link from list of arXiv links.

        :param links: List of dictionaries containing link data
        :returns: URL string for PDF download or None if not found
        :logs: Debug message if no links, warning if PDF link missing
        """
        if not links:
            self.logger.debug("No links found.")
            return None
        for link in links:
            if "/pdf" in link["href"]:
                return link["href"]
        self.logger.warning(f"Missing 'pdf' in links: {links}")
        return None

    def get(self, arxiv_data: dict) -> dict:
        """
        Get cleaned paper metadata with standard structure.

        :param arxiv_data: Raw arXiv paper metadata
        :returns: Dictionary with standardized paper metadata
        :raises KeyError: If required metadata fields are missing
        """
        try:
            return {
                "id": arxiv_data.get("id", None),
                "updated": arxiv_data.get("updated", None),
                "published": arxiv_data.get("published", None),
                "title": arxiv_data.get("title", None),
                "summary": arxiv_data.get("summary", None),
                "author": arxiv_data.get("author", None),
                "links": arxiv_data.get("links", None),
                "category": arxiv_data.get("category", None),
                "primary_category": arxiv_data.get("primary_category", None),
                "content": arxiv_data.get("content", None),
            }
        except KeyError as e:
            raise KeyError(f"Missing key in dict data: {e}")

    def __get_raw(self, arxiv_data: dict) -> dict:
        """
        Extract and clean raw arXiv metadata fields.

        :param arxiv_data: Raw XML-parsed arXiv metadata
        :returns: Dictionary with cleaned metadata fields
        :raises KeyError: If required raw data fields are missing
        :note: Private method for internal metadata processing
        """
        try:
            return {
                "id": arxiv_data.get("id", {}).get("#text", None),
                "updated": arxiv_data.get("updated", {}).get("#text", None),
                "published": arxiv_data.get("published", {}).get("#text", None),
                "title": clean_text(arxiv_data.get("title", {}).get("#text", None)),
                "summary": arxiv_data.get("summary", {}).get("#text", None),
                "author": extract_authors(arxiv_data.get("author", None)),
                "links": extract_links(arxiv_data.get("link", None)),
                "category": extract_category(arxiv_data.get("category", None)),
                "primary_category": extract_primary_category(
                    arxiv_data.get("primary_category", None)
                ),
            }
        except KeyError as e:
            raise KeyError(f"Missing key in raw data: {e}")

    def process_item(self, item: dict, overwrite: Optional[bool] = False) -> None:
        """
        Process single arXiv paper item - extract metadata and download PDF.

        :param item: Raw paper metadata from arXiv API
        :param overwrite: Whether to overwrite existing files
        :logs: Warning if PDF link not found
        """
        item_summary = self.__get_raw(item)
        pdf_link = self.extract_pdf_link(item_summary.get("links"))

        if pdf_link:
            item_summary["content"] = clean_text(load_pdf_text(pdf_link))
            save_to_file(
                self.get(item_summary), item_summary["title"], add_timestamp=overwrite
            )
        else:
            self.logger.warning(
                f"No pdf link. File not downloadable for {item_summary['title']}"
            )

    def fetch_and_process(
        self, query: Query, overwrite: Optional[bool] = False
    ) -> None:
        """
        Fetch papers from arXiv API and process results concurrently.

        :param query: Query parameters for arXiv API
        :param overwrite: Whether to overwrite existing files
        :raises httpx.HTTPError: If API request fails
        :logs: Error for failed processing, warning if no content
        """
        response = self.client.get(f"{self.base_url}{query.build()}")
        response.raise_for_status()
        embedded_data = xml_to_dict(response.text)

        if "entry" in embedded_data.keys():
            embedded_data = embedded_data.get("entry")
            futures = [
                self.executor.submit(self.process_item, item, overwrite)
                for item in embedded_data
            ]
            done, _ = wait(futures)
            for future in done:
                if future.exception():
                    self.logger.error(f"Error processing item: {future.exception()}")
        else:
            self.logger.warning("No PDF content to extract")

    def download_papers(
        self, queries: List[Query], overwrite: Optional[bool] = False
    ) -> None:
        """
        Request and process multiple arXiv queries sequentially.

        :param queries: List of Query objects with search parameters
        :param overwrite: Whether to overwrite existing files
        :logs: Info about progress, debug for file paths
        """
        self.logger.info(f"Getting papers. Quereies to process: {len(queries)}")
        self.logger.debug(f"File download path: {self.download_path}")

        try:
            for query in queries:
                self.fetch_and_process(query=query, overwrite=overwrite)
            self.logger.info("Saved all papers as json files.")
        except Exception as e:
            raise PaperGeneralError(f"Failed to get papers: {e}")


    async def read_papers(
        self, 
        queries: List[Query],
        prettify: Optional[bool] = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Fetch and yield papers content one by one from arXiv API.
        
        :param queries: List of Query objects with search parameters
        :param prettify: Optional bool. If set to True, dumps dict to json with indent ==  4.
        :yields: Dictionary containing full paper metadata and content
        :raises: httpx.HTTPError: If API request fails
        """
        self.logger.info(f"Reading papers. Queries to process: {len(queries)}")

        for query in queries:
            try:
                response = self.client.get(f"{self.base_url}{query.build()}")
                response.raise_for_status()
                embedded_data = xml_to_dict(response.text)
                if "entry" not in embedded_data:
                    self.logger.warning("No entries found for query")
                    continue
                entries = embedded_data.get("entry")
                if not isinstance(entries, list):
                    entries = [entries]  
                for item in entries:
                    try:
                        item_summary = self.__get_raw(item)
                        pdf_link = self.extract_pdf_link(item_summary.get("links"))
                        if pdf_link:
                            item_summary["content"] = clean_text(load_pdf_text(pdf_link))
                            yield json.dumps(self.get(item_summary), indent=4) if prettify else self.get(item_summary)
                        else:
                            self.logger.warning(
                                f"No PDF link for {item_summary.get('title')}"
                            )
                    except Exception as e:
                        self.logger.error(f"Error processing paper: {e}")
                        continue  
            except httpx.HTTPError as e:
                self.logger.error(f"HTTP error for query {query}: {e}")
                continue
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                continue
