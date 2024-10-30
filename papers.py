import os
import httpx
import logging
from paper_builer import Query
from pyinstrument import Profiler
from concurrent.futures import wait
from typing import Final, Optional, List
from concurrent.futures import ThreadPoolExecutor
from custom_logger import setup_logger, null_logger

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


class ArxivSummary:
    def __init__(self, arxiv_data: dict):
        self.arxiv_data = arxiv_data

    def get(self) -> dict:
        return {
            "id": self.arxiv_data.get("id", {}).get("#text"),
            "updated": self.arxiv_data.get("updated", {}).get("#text"),
            "published": self.arxiv_data.get("published", {}).get("#text"),
            "title": clean_text(self.arxiv_data.get("title", {}).get("#text")),
            "summary": self.arxiv_data.get("summary", {}).get("#text"),
            "author": extract_authors(self.arxiv_data.get("author", {})),
            "links": extract_links(self.arxiv_data.get("link", {})),
            "category": extract_category(self.arxiv_data.get("category", {})),
            "primary_category": extract_primary_category(
                self.arxiv_data.get("primary_category", {})
            ),
        }


class ArxivPaper:
    def __init__(self, arxiv_data: dict, client: Optional[httpx.Client] = None):
        self.client = client if client else httpx.Client()
        self.arxiv_data = arxiv_data

    def get(self) -> dict:
        return {
            "id": self.arxiv_data.get("id", None),
            "updated": self.arxiv_data.get("updated", None),
            "published": self.arxiv_data.get("published", None),
            "title": self.arxiv_data.get("title", None),
            "summary": self.arxiv_data.get("summary", None),
            "author": self.arxiv_data.get("author", None),
            "links": self.arxiv_data.get("links", None),
            "category": self.arxiv_data.get("category", None),
            "primary_category": self.arxiv_data.get("primary_category", None),
            "content": self.arxiv_data.get("content", None),
        }


class Arxiv:
    def __init__(
        self,
        max_workers: Optional[int] = 100,
        logger: Optional[bool] = False,
        log_level: Optional[str] = "info",
        base_url: Optional[str] = "http://export.arxiv.org/api/query?",
    ):
        self.logger = (
            setup_logger(name=os.path.basename(__file__), log_level=log_level)
            if logger
            else null_logger()
        )
        self.client = httpx.Client()
        self.base_url: Final[str] = base_url
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def extract_pdf_link(self, links: list) -> Optional[str]:
        for link in links:
            if "/pdf" in link["href"]:
                return link["href"]
        self.logger.debug(f"Missing PDF in links: {links}")
        return None

    def process_item(self, item: dict) -> None:
        item_summary = ArxivSummary(item).get()
        pdf_link = self.extract_pdf_link(item_summary.get("links"))
        if pdf_link:
            content = clean_text(load_pdf_text(pdf_link))
            item_summary["content"] = content if content else None
            save_to_file(ArxivPaper(item_summary).get(), item_summary["title"])

    def fetch_and_process(self, query: Query) -> None:
        response = self.client.get(f"{self.base_url}{query.build()}")
        response.raise_for_status()
        embedded_data = xml_to_dict(response.text)

        if "entry" in embedded_data.keys():
            embedded_data = embedded_data.get("entry")
            futures = [
                self.executor.submit(self.process_item, item) for item in embedded_data
            ]
            done, _ = wait(futures)
            for future in done:
                if future.exception():
                    self.logger.error(f"Error processing item: {future.exception()}")

    def papers_save(
        self, queries: List[Query], save_path: Optional[str] = "ArxivPapers"
    ) -> None:
        save_path = check_path(save_path)
        for query in queries:
            self.fetch_and_process(query)

