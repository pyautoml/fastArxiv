
"""
Custom exceptions for the arXiv API client.

This module defines custom exceptions used throughout the arXiv client
to provide more specific error handling and better error messages.
These exceptions help distinguish between different types of failures
that can occur during API interactions, paper downloads, and processing.
"""

class PDFDownloadError(Exception):
    """Base exception for PDF download/processing errors."""
    pass


class XMLParsingError(Exception):
    """Custom exception for XML parsing errors."""
    pass


class PaperGeneralError(Exception):
    """Custom exception for XML parsing errors."""
    pass
