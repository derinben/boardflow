"""FastAPI application factory and configuration."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .dependencies import get_engine
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    logger.info("Starting BoardFlow API")
    logger.info(f"Database: {os.environ.get('DATABASE_URL', 'Not configured')[:50]}...")
    logger.info(f"LLM API Key: {'Configured' if os.environ.get('ANTHROPIC_API_KEY') else 'Missing'}")

    yield

    # Shutdown
    logger.info("Shutting down BoardFlow API")
    engine = get_engine()
    if engine:
        await engine.dispose()
        logger.info("Database connection pool disposed")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI app instance.
    """
    app = FastAPI(
        title="BoardFlow API",
        description="Board game recommendation engine powered by LLM and collaborative filtering",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware (adjust origins for production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    app.include_router(router, prefix="/api")

    return app
