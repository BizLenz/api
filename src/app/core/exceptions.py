from .config import settings
from fastapi import HTTPException, logger


# TODO: Add more specific exception handling
def to_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, HTTPException):
        return error

    logger.logger.error(f"Unhandled exception: {error}", exc_info=True)

    if settings.debug:
        detail_message = str(error)
    else:
        detail_message = "An unexpected server error occurred."

    return HTTPException(status_code=500, detail=detail_message)