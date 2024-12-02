"""
Utility functions for arXiv paper processing and file management.

This module provides helper functions for:
- PDF file downloading and text extraction
- XML parsing and data cleaning
- File path management and validation
- Text cleaning and normalization
- File name sanitization
- Data saving and loading
- Custom exception handling

The utilities support the main arXiv client operations by providing
lower-level file and data processing capabilities.

Constants:
    DEFAULT_ARXIV_DIR: Default directory for paper storage
    INVALID_FILENAME_CHARS: Mapping of invalid characters for filenames

Dependencies:
    - httpx: For HTTP requests
    - pypdf: For PDF processing
    - pathlib: For path operations
    - xml.etree: For XML parsing
"""

import os
import json
import httpx
import logging
from io import BytesIO
from uuid import uuid4
from pathlib import Path
from pypdf import PdfReader
from datetime import datetime
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from typing import Any, Dict, Final, List, Optional
from .custom_exceptions import PDFDownloadError, XMLParsingError


logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)


DEFAULT_ARXIV_DIR: Final[str] = "ArxivPapers"
INVALID_FILENAME_CHARS: Final[Dict] = {
    " ": "_",
    ":": "",
    "\\": "",
    "/": "",
    "'": "",
    '"': "",
    "-": "",
    "@": "",
    "\t": "",
    "\n": "",
    "\n\n": "",
    "?": "",
    "!": "",
    "__": "_",
}
CHAR_REPLACEMENTS: Final[List[tuple]] = [
    ("\n", " "),
    ("\t", " "),
    ("\n\n", " "),
    ("\t\t", " "),
    ("  ", " "),
    ("#text", ""),
]


def clean_filename(text: str) -> str:
    """
    Clean filename by removing/replacing invalid characters.

    :param text: (str) Filename to clean
    :returns: Cleaned filename string
    """
    if not text or not isinstance(text, str):
        return str(uuid4().hex)
    for char, replacement in INVALID_FILENAME_CHARS.items():
        text = text.replace(char, replacement)
    return text


def clean_text(text: str) -> str | Any:
    """
    Clean text by normalizing whitespace and removing special characters.

    :param text: (str) Text to clean of text is a string, else return Any
    :returns: Cleaned text string
    """
    if not text or not isinstance(text, str):
        return text
    for old, new in CHAR_REPLACEMENTS:
        text = text.replace(old, new)
    return text.strip()


def clean_paper_chunk(text: str) -> str | Any:
    """
    Clean paper text chunk by handling escaped characters.

    :param text: (str) Text chunk to clean
    :returns: Cleaned text string is provded data is string, or Any otherwise
    """
    if not text or not isinstance(text, str):
        return text
    return text.replace(r"\\n", "\n").replace(r"\\t", "\t")


def posix_path(path_: str = None) -> str:
    """
    Convert Windows path to POSIX-style absolute path.

    :param path_: (str, optional) Path to convert. If None, returns current directory
    :returns: Absolute path in POSIX format (forward slashes)
    :raises TypeError: If path_ is not str or Path object
    """
    if path_ and isinstance(path_, (Path | str)):
        return Path(
            os.path.abspath(os.path.join(os.path.dirname(__file__), path_))
        ).as_posix()
    return Path(os.path.abspath(os.path.join(os.path.dirname(__file__)))).as_posix()


def check_path(path: str = "ArxivPapers") -> Path:
    """
    Check if path exists and create if needed, normalizing to absolute path.

    :param path: (str) Directory path to check/create
    :returns: Path object with absolute POSIX-style path
    :raises OSError: If directory creation fails
    """
    try:
        abs_path = os.path.abspath(path)
        posix_abs_path = posix_path(abs_path)

        if os.path.exists(posix_abs_path):
            return Path(posix_abs_path)

        try:
            os.makedirs(posix_abs_path, mode=0o755)
            return Path(posix_abs_path)
        except OSError as e:
            default_path = os.path.join(os.path.dirname(__file__), DEFAULT_ARXIV_DIR)
            default_posix_path = posix_path(default_path)
            
            if os.path.exists(default_posix_path):
                return Path(default_posix_path)
                
            os.makedirs(default_posix_path, mode=0o755)
            return Path(default_posix_path)

    except Exception as e:
        raise OSError(f"Path operation failed: {e}")


def create_timestamp() -> str:
    """
    Create a compact timestamp string.

    :returns: Timestamp in format 'YYYYMMDDhhmmss'
    """
    return datetime.now().strftime("%Y%m%d%H%M%S")


def non_empty_check(
    variable: Any, expected_type: Any, variable_name: Optional[str] = None
) -> None:
    """
    Validate that a variable is non-empty and of expected type.

    :param variable: Variable to check
    :param expected_type: Expected type of the variable
    :param variable_name: Optional name for error messages
    :raises TypeError: If variable is not of expected_type
    :raises ValueError: If variable is empty
    """
    if not isinstance(variable, expected_type):
        raise TypeError(f"Expected {expected_type}, got {type(variable)}")
    if not variable:
        name = variable_name or "Variable"
        raise ValueError(f"{name} cannot be empty")


def save_to_file(
    data: dict,
    file_name: str,
    path: str = "ArxivPapers",
    add_timestamp: Optional[bool] = False,
) -> None:
    """
    Save data to JSON file.

    :param data: Dictionary to save
    :param file_name: Target filename
    :param path: Directory path
    :param add_timestamp: Whether to add timestamp to filename
    :raises OSError: If file cannot be written
    """
    if not file_name:
        file_name = f"{uuid4().hex}"
    try:
        file_name = clean_filename(file_name)
        if add_timestamp:
            file_path = f"{path}/{file_name}_{create_timestamp()}.json"
        else:
            file_path = f"{path}/{file_name}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        raise OSError(f"Could not save file: {e}")


def xml_to_dict(xml_data: str) -> dict:
    """
    Convert XML string to dictionary representation.

    :param xml_data: (str) XML string to parse
    :returns: Dictionary representation of XML
    :raise XMLParsingError: If XML parsing fails
    :raise ValueError: If input is empty or invalid
    """
    try:
        result = {}
        element = ET.fromstring(xml_data.strip())

        if element.attrib:
            result.update({f"@{key}": value for key, value in element.attrib.items()})

        for child in element:
            # Remove XML namespace if present
            tag = child.tag.split("}")[-1]
            try:
                child_dict = xml_to_dict(ET.tostring(child, encoding="unicode"))
            except ET.ParseError as e:
                raise XMLParsingError(f"Failed to parse child element '{tag}: {e}")

            if tag in result:
                if not isinstance(result[tag], list):
                    result[tag] = [result[tag]]
                result[tag].append(child_dict)
            else:
                result[tag] = child_dict

        if element.text and element.text.strip():
            result["#text"] = element.text.strip()
        return result
    except ET.ParseError as e:
        raise XMLParsingError(f"Failed to parse XML data: {e}")
    except Exception as e:
        raise XMLParsingError(f"Unexpected error processing XML: {e}")


def extract_authors(author: Optional[Dict | List[Dict]]) -> List[str]:
    """
    Extract author names from arXiv metadata.

    :param author: Dictionary or list of dictionaries containing author data
    :returns: List of author names, excluding None values
    :raises TypeError: If input is not None, dict or list
    """
    if not author:
        return []

    if not isinstance(author, (dict, list)):
        raise TypeError(f"Expected dict or list, got {type(author)}")

    # Handle single author
    if isinstance(author, dict):
        name = author.get("name", {}).get("#text")
        return [name] if name else []

    # Handle list of authors
    names = [person.get("name", {}).get("#text") for person in author]
    return list(filter(None, names))


def extract_links(link: Optional[Dict | List[Dict]]) -> List[Dict[str, Optional[str]]]:
    """
    Extract links data from arXiv metadata.

    :param link: Dictionary or list of dictionaries containing link data
    :returns: List of dictionaries with href, rel and type information
    :raises TypeError: If input is not None, dict or list
    """
    if not link:
        return []

    if not isinstance(link, (dict, list)):
        raise TypeError(f"Expected dict or list, got {type(link)}")

    # Handle single link
    if isinstance(link, dict):
        return [
            {
                "href": link.get("@href"),
                "rel": link.get("@rel"),
                "type": link.get("@type"),
            }
        ]

    # Handle list of links using list comprehension
    return [
        {"href": url.get("@href"), "rel": url.get("@rel"), "type": url.get("@type")}
        for url in link
        if url
    ]


def extract_category(category: Dict | List[Dict]) -> List[str]:
    """
    Extract unique category terms from arXiv metadata.

    :param category: Dictionary or list of dictionaries containing category data
    :returns: List of unique category terms, excluding None values
    :note: Schema is always 'http://arxiv.org/schemas/atom'
    """
    if not category:
        return []

    if not isinstance(category, (dict, list)):
        raise TypeError(f"Expected dict or list, got {type(category)}")

    if isinstance(category, dict):
        term = category.get("@term")
        return [term] if term else []

    terms = [entry.get("@term") for entry in category if entry]
    return list(set(filter(None, terms)))


def extract_primary_category(
    primary_category: Optional[Dict[str, str]]
) -> Optional[str]:
    """
    Extract primary category term from arXiv metadata.

    :param primary_category: Dictionary containing primary category data
    :returns: Primary category term or None if not found
    :note: Schema is always 'http://arxiv.org/schemas/atom'
    :raises TypeError: If input is not None or dict
    """
    if not primary_category:
        return None
    if not isinstance(primary_category, dict):
        raise TypeError(f"Expected dict or None, got {type(primary_category)}")
    return primary_category.get("@term")


def load_pdf_text(url: str, timeout: float = 30.0) -> Optional[str]:
    """
    Download and extract text content from a PDF URL.

    :param url: (str) URL of the PDF to download and process
    :param timeout: (float) Request timeout in seconds, 30 seconds by default
    :param silent_error: (bool) Whether to return None on errors instead of raising
    :returns: Extracted text content or None if extraction fails and silent_error=True
    :raise ValueError: If URL is invalid
    :raise PDFDownloadError: If PDF download or processing fails
    :raise httpx.TimeoutException: If request times out
    """
    if not url or not urlparse(url).scheme:
        raise ValueError(f"Invalid URL: {url}")
    try:
        client = httpx.Client(timeout=timeout)
        with client:
            response = client.get(url, follow_redirects=True)
            response.raise_for_status()
            pdf_reader = PdfReader(BytesIO(response.content))
            if not pdf_reader.pages:
                raise PDFDownloadError(f"No pages found in PDF from {url}")

            text = "".join(
                clean_paper_chunk(page.extract_text())
                for page in pdf_reader.pages
                if page.extract_text()  # Skip empty pages
            )
            if not text.strip():
                raise PDFDownloadError(f"No text content extracted from {url}")
            return text
    except httpx.TimeoutException as e:
        raise PDFDownloadError(f"Timeout downloading PDF from {url}: {e}")
    except httpx.HTTPError as e:
        raise PDFDownloadError(f"HTTP error downloading PDF from {url}: {e}")
    except Exception as e:
        raise PDFDownloadError(f"Error processing PDF from {url}: {e}")
