"""
arXiv API query builder and validator.
This module provides components for building and validating arXiv API queries:

Components:
    - SortBy: Enum for result sorting options (relevance, date)
    - SortOrder: Enum for sort direction (asc/desc)
    - Area: Enum for search areas (title, author, abstract, etc.)
    - Query: Pydantic model for building validated query strings

Example:
    >>> query = Query(
    ...     search_query="machine learning",
    ...     area=Area.title,
    ...     max_results=5,
    ...     sort_by=SortBy.relevance
    ... )
    >>> query.build()
    'search_query=ti:machine learning&start=0&max_results=5&sort_by=relevance&sort_order=descending'

Dependencies:
    - pydantic: For data validation
    - enum: For enumerated types
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, PositiveInt, Field, field_validator


class SortBy(str, Enum):
    """
    Enum for arXiv API result sorting options.
    :cvar relevance: Sort by relevance score
    :cvar submittedDate: Sort by paper submission date
    :cvar lastUpdatedDate: Sort by last update date
    """

    relevance = "relevance"
    submittedDate = "submittedDate"
    lastUpdatedDate = "lastUpdatedDate"

    @classmethod
    def values(cls):
        """Return a list of all values in the SortBy enum."""
        return list(cls.__members__.values())


class SortOrder(str, Enum):
    """
    Enum for sort order direction.
    :cvar ascending: Sort in ascending order
    :cvar descending: Sort in descending order
    """

    ascending = "ascending"
    descending = "descending"

    @classmethod
    def values(cls):
        """Return a list of all values in the SortOrder enum."""
        return list(cls.__members__.values())


class Area(str, Enum):
    """
    Enum for arXiv API search areas.
    :cvar all_: Search all fields
    :cvar title: Search only titles
    :cvar author: Search by author
    :cvar abstract: Search in abstracts
    :cvar comment: Search in comments
    :cvar journalreference: Search journal references
    :cvar subjectcategory: Search by subject category
    :cvar reportnumber: Search by report number
    :cvar idlist: Search by arXiv ID list
    """

    all_ = "all"
    title = "ti"
    author = "au"
    abstract = "abs"
    comment = "co"
    journalreference = "jr"
    subjectcategory = "cat"
    reportnumber = "rn"
    idlist = "id_list"

    @classmethod
    def values(cls):
        """Return a list of all values in the Area enum."""
        return list(cls.__members__.values())


class Query(BaseModel):
    """
    Model for building and validating arXiv API queries.
    :ivar search_query: (str) Main search terms.
    :ivar area: (Area) Search area to query.
    :ivar id_list: (List[int]) Comma-separated list of arXiv IDs.
    :ivar start: (int) Starting index for results.
    :ivar max_results: (int) Maximum number of results to return.
    :ivar sort_by: (SortBy) How to sort results.
    :ivar sort_order: (SortOrder) Order of sorting.
    """

    search_query: str
    area: Optional[str] = Field(
        default=Area.all_.value,
        description="Narrowed down search area, e.g. 'author', 'list_id', etc.",
    )
    id_list: Optional[str] = Field(default=None, description="Comma-delimited string")
    start: PositiveInt = Field(default=0, ge=0)
    max_results: PositiveInt = Field(default=1, ge=1)
    sort_by: Optional[str] = Field(
        default="relevance",
        description="Sort by relevance, submission date or last update date",
    )
    sort_order: Optional[str] = Field(
        default="descending", description="Order of sorting: ascending or descending"
    )

    def build(self) -> str:
        """
        Build a query string based on the instance attributes.
        :returns: Formatted query string for arXiv API
        """
        return (
            f"search_query={self.area}:{self.search_query}&"
            f"start={self.start}&"
            f"max_results={self.max_results}&"
            f"sort_by={self.sort_by}&"
            f"sort_order={self.sort_order}"
        )

    @field_validator("area")
    def validate_area(cls, value):
        """
        Validate search area value.
        :raises ValueError: If value not in Area enum
        """
        if value not in Area.values:
            raise ValueError(
                f"Error in 'Area': must be in '{', '.join([x for x in Area.values])}', not: (input: '{value}')"
            )
        return value

    @field_validator("search_query")
    def check_length(cls, value):
        """
        Validate search query length.
        :raises ValueError: If query length <= 1
        """
        if len(value) <= 1:
            raise ValueError("search_query must be longer than 1 character")
        return value

    @field_validator("sort_by")
    def validate_sort_by(cls, value):
        """
        Validate sort_by value.
        :raises ValueError: If value not in SortBy enum
        """
        if value not in SortBy.values:
            raise ValueError(
                f"Error in 'sort_by': must be either 'relevance', 'submittedDate' or 'lastUpdatedDate', not: (input: '{value}')"
            )
        return value

    @field_validator("sort_order")
    def validate_sort_order(cls, value):
        """
        Validate sort order value.
        :raises ValueError: If value not in SortOrder enum
        """
        value = value.lower() if value else value
        if value not in SortOrder.values:
            raise ValueError(
                f"Error in 'sort_order': must be either 'ascending' or 'descending', not: (input: '{value}')"
            )
        return value
