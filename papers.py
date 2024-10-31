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
    extract_primary_category
)

logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)


class Arxiv:
    def __init__(
        self,
        log_level: Optional[str] = "info",
        max_workers: Optional[int] = 100,
        logger: Optional[bool | logging.Logger] = False,
        download_path: Optional[str] = check_path("ArxivPapers"),
        base_url: Optional[str] = "http://export.arxiv.org/api/query?",
    ):
        self.client = httpx.Client()
        self.base_url: Final[str] = base_url
        self.download_path = check_path(download_path)
        self.logger = self.__setup_logger(logger, log_level)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def __setup_logger(
        self, logger: Optional[bool | logging.Logger], log_level: str
    ) -> logging.Logger:
        if not logger:
            return null_logger()
        if isinstance(logger, bool):
            return setup_logger(name=os.path.basename(__file__), log_level=log_level)
        return logger

    def extract_pdf_link(self, links: list) -> Optional[str]:
        if not links:
            self.logger.debug("No links found.")
            return None
        for link in links:
            if "/pdf" in link["href"]:
                return link["href"]
        self.logger.warning(f"Missing 'pdf' in links: {links}")
        return None

    def get(self, arxiv_data: dict) -> dict:
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
        try:
            return {
                "id": arxiv_data.get("id", {}).get("#text"),
                "updated": arxiv_data.get("updated", {}).get("#text"),
                "published": arxiv_data.get("published", {}).get("#text"),
                "title": clean_text(arxiv_data.get("title", {}).get("#text")),
                "summary": arxiv_data.get("summary", {}).get("#text"),
                "author": extract_authors(arxiv_data.get("author", {})),
                "links": extract_links(arxiv_data.get("link", {})),
                "category": extract_category(arxiv_data.get("category", {})),
                "primary_category": extract_primary_category(
                    arxiv_data.get("primary_category", {})
                ),
            }
        except KeyError as e:
            raise KeyError(f"Missing key in raw data: {e}")

    def process_item(self, item: dict) -> None:
        item_summary = self.__get_raw(item)
        pdf_link = self.extract_pdf_link(item_summary.get("links"))

        if pdf_link:
            content = clean_text(load_pdf_text(pdf_link))
            item_summary["content"] = content if content else None
            save_to_file(self.get(item_summary), item_summary["title"])
        else:
            self.logger.warning(
                f"No pdf link. File not downloadable for {item_summary['title']}"
            )

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
        else:
            self.logger.warning("No PDF content to extract")

    def get_papers(self, queries: List[Query]) -> None:
        self.logger.info(f"Getting papers. Quereies to process: {len(queries)}")
        self.logger.debug(f"File download path: {self.download_path}")
        for query in queries:
            self.fetch_and_process(query)
        self.logger.info("Saved all papers as json files.")

