import os
import time
import fitz
import json
import httpx
import logging
from uuid import uuid4
from typing import Any
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)


def clean_filename(text: str) -> str:
    return (
        f"{text}".replace(" ", "_")
        .replace(":", "")
        .replace("\\", "")
        .replace("/", "")
        .replace("'", "")
        .replace('"', "")
        .replace("-", "")
        .replace("@", "")
        .replace("\t", "")
        .replace("\n", "")
        .replace("\n\n", "")
        .replace("?", "")
        .replace("!", "")
        .replace("__", "_")
    )


def clean_text(text: str) -> str:
    if not text:
        return text
    return (
        text.replace("\n", " ")
        .replace("\t", " ")
        .replace("\n\n", " ")
        .replace("\t\t", " ")
        .replace("  ", " ")
        .replace("#text", "")
    )


def clean_paper_chunk(text: str) -> str:
    if not text:
        return text
    return text.replace(r"\\n", "\n").replace(r"\\t", "\t")


def check_path(path: str = "ArxivPapers") -> Path:
    if not os.path.exists(path):
        path = Path(
            os.path.abspath(os.path.join(os.path.dirname(__file__), path))
        ).as_posix()
        if not os.path.exists(path):
            path = Path(
                os.path.abspath(os.path.join(os.path.dirname(__file__), "ArxivPapers"))
            ).as_posix()
            os.mkdir(path, mode=0o755)
    else:
        path = Path(path).as_posix()
    return path


def create_timestamp() -> str:
    return (
        str(datetime.now().replace(microsecond=0))
        .replace("-", "")
        .replace(" ", "")
        .replace(":", "")
    )


def non_empty_check(variable: Any, expected_type: Any, variable_name: str = None):
    if not isinstance(variable, expected_type):
        raise TypeError(f"Expected {expected_type} type, got {type(variable)}")
    if not variable:
        raise ValueError(
            f"{'Variable' if not variable_name else variable_name} cannot be empty."
        )


def save_to_file(data: dict, file_name: str, path: str = "ArxivPapers") -> None:
    if not file_name:
        file_name = f"{uuid4().hex}"
    file_name = clean_filename(file_name)
    timestamp = create_timestamp()
    file_path = f"{path}/{file_name}_{timestamp}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def xml_to_dict(xml_data) -> dict:
    try:
        element = ET.fromstring(xml_data.strip())
    except ET.ParseError as e:
        raise Exception(f"Failed to parse XML data. Parsing error: {e}")

    result = {}
    if element.attrib:
        result.update({f"@{key}": value for key, value in element.attrib.items()})

    for child in element:
        tag = child.tag.split("}")[-1]  # Remove XML namespace if present
        try:
            child_dict = xml_to_dict(ET.tostring(child, encoding="unicode"))
        except ET.ParseError as e:
            raise Exception(f"Failed to parse child element '{tag}'. Error: {e}")

        # Manage multiple occurrences of the same tag
        if tag in result:
            if not isinstance(result[tag], list):
                result[tag] = [result[tag]]
            result[tag].append(child_dict)
        else:
            result[tag] = child_dict

    if element.text and element.text.strip():
        result["#text"] = element.text.strip()
    return result


def extract_authors(author: dict) -> list:
    authors = []

    if not author:
        return authors

    if isinstance(author, list):
        for person in author:
            authors.append(person.get("name", {}).get("#text"))
    return authors


def extract_links(link: dict) -> list:
    links = []

    if not link:
        return links

    if isinstance(link, list):
        for url in link:
            links.append(
                {
                    "href": url.get("@href"),
                    "rel": url.get("@rel"),
                    "type": url.get("@type"),
                }
            )
    return links


def extract_category(category: dict) -> list:
    """Additionally: "scheme": entry.get("@scheme") where scheme is always == http://arxiv.org/schemas/atom"""
    cat = []
    if not category:
        return cat

    if isinstance(category, list):
        for entry in category:
            cat.append(entry.get("@term"))
    return cat


def extract_primary_category(primary_category: dict) -> dict:
    """Additionally: "scheme": entry.get("@scheme") where scheme is always == http://arxiv.org/schemas/atom"""
    if not primary_category:
        return {}
    return primary_category.get("@term")


def load_pdf_text(url: str) -> str:
    non_empty_check(url, str, "url")
    if "pdf" not in url:
        None
    try:
        with httpx.Client() as client:
            response = client.get(url, follow_redirects=True)
            response.raise_for_status()
            pdf_reader = fitz.open(stream=response.content, filetype="pdf")
            text = "".join(clean_paper_chunk(page.get_text()) for page in pdf_reader)
            pdf_reader.close()
        return text
    except Exception:
        return None
