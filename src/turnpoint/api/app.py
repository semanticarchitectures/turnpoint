"""Turnpoint REST API (decision 0003: the only surface the viewer talks to).

Run with ``turnpoint-api``, or ``uvicorn turnpoint.api.app:app`` directly.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from turnpoint import NOT_FOR_OPERATIONAL_USE, __version__
from turnpoint.api.routes import router

app = FastAPI(title="Turnpoint API", version=__version__, description=NOT_FOR_OPERATIONAL_USE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("TURNPOINT_CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "turnpoint-api", "version": __version__, "notice": NOT_FOR_OPERATIONAL_USE}


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
