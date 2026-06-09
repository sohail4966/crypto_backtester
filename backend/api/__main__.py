"""
Run the Phase 4 API server with uvicorn.
"""

from __future__ import annotations

import uvicorn

from api import settings


def main() -> None:
    """Start uvicorn with configured host and port."""
    uvicorn.run(
        "api.main:app",
        host=settings.api_host(),
        port=settings.api_port(),
        reload=False,
    )


if __name__ == "__main__":
    main()
