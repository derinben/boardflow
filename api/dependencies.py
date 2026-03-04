"""FastAPI dependency injection for database and services."""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services import LLMService

# Database engine (singleton)
_engine = None
_session_factory = None


def get_database_url() -> str:
    """Get database URL from environment."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL environment variable not set")

    # Convert to async URL if needed
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def get_engine():
    """Get or create database engine singleton."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            get_database_url(),
            pool_size=10,
            max_overflow=5,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


def get_session_factory() -> async_sessionmaker:
    """Get or create session factory singleton."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database session.

    Usage in endpoint:
        async def endpoint(session: AsyncSession = Depends(get_db_session)):
            ...
    """
    factory = get_session_factory()
    async with factory() as session:
        yield session


def get_llm_service() -> LLMService:
    """Dependency for LLM service.

    Usage in endpoint:
        async def endpoint(llm: LLMService = Depends(get_llm_service)):
            ...
    """
    return LLMService()
