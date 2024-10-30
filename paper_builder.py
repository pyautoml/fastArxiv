from enum import Enum
from typing import Optional
from pydantic import BaseModel, PositiveInt, Field, field_validator


class SortBy(str, Enum):
    relevance = "relevance"
    submittedDate = "submittedDate"
    lastUpdatedDate = "lastUpdatedDate"

    @classmethod
    def values(cls):
        """Return a list of all values in the SortBy enum."""
        return list(cls.__members__.values())


class SortOrder(str, Enum):
    ascending = "ascending"
    descending = "descending"

    @classmethod
    def values(cls):
        """Return a list of all values in the SortOrder enum."""
        return list(cls.__members__.values())


class Area(str, Enum):
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
        """Return a list of all values in the IdList enum."""
        return list(cls.__members__.values())


class Query(BaseModel):
    search_query: str
    area: Optional[str] = Field(
        default=Area.all_.value,
        description="Narrowed down seach area, e.g. 'author', 'list_id', etc.",
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
        """Builds a query string based on the instance attributes."""
        # return "search_query=all:electron&start=0&max_results=1"
        return (
            f"search_query={self.area}:{self.search_query}&"
            f"start={self.start}&"
            f"max_results={self.max_results}&"
            f"sort_by={self.sort_by}&"
            f"sort_order={self.sort_order}"
        )

    @field_validator("area")
    def validate_area(cls, value):
        if value not in Area.values:
            raise ValueError(
                f"Error in 'Area': must be in '{', '.join([x for x in Area.values])}', not: (input: '{value}')"
            )
        return value

    @field_validator("search_query")
    def check_length(cls, value):
        if len(value) <= 1:
            raise ValueError("search_query must be longer than 1 character")
        return value

    @field_validator("sort_by")
    def validate_sort_by(cls, value):
        if value not in SortBy.values:
            raise ValueError(
                f"Error in 'sort_by': must be either 'relevance', 'submittedDate' or 'lastUpdatedDate', not: (input: '{value}')"
            )
        return value

    @field_validator("sort_order")
    def validate_sort_order(cls, value):
        value = value.lower() if value else value
        if value not in SortOrder.values:
            raise ValueError(
                f"Error in 'sort_order': must be either 'ascending' or 'descending', not: (input: '{value}')"
            )
        return value
