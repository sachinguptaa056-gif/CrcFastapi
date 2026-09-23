from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import create_db_and_tables
from app.routers import events, reservations


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle handler."""
    # Automatically create SQLite tables on startup
    create_db_and_tables()
    yield


app = FastAPI(
    title="College Event & Reservation Management API",
    description=(
        "A FastAPI REST API built with SQLModel and SQLite for managing college events "
        "(workshops, hackathons, seminars) and automated student seat reservations."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable CORS for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(events.router)
app.include_router(reservations.router)


@app.get("/", tags=["Health & Root"], summary="API Root / Health Check")
def root():
    return {
        "message": "Welcome to the College Event & Reservation Management API",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "status": "online",
    }
