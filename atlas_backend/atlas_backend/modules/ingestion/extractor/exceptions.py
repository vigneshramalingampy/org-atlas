class DocumentExtractionError(Exception):
    """Raised when a document cannot be parsed or extracted.

    Wraps lower-level errors (file not found, corrupt file, parse error)
    into a single exception type the ingestion service can catch uniformly.
    """
