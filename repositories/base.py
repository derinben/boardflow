"""Base repository with session management utilities."""

from typing import AsyncContextManager, Callable

from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """Base class for all repositories.

    Provides common utilities for database access via AsyncSession.
    Session lifecycle is managed by the caller (service layer or endpoint).
    """

    def __init__(self, session_factory: Callable[[], AsyncContextManager[AsyncSession]]):
        """Initialize repository with an async session factory.

        Args:
            session_factory: Callable that returns an async context manager
                           for AsyncSession (e.g., async_sessionmaker instance).
        """
        self._session_factory = session_factory

    async def get_session(self) -> AsyncSession:
        """Get a new async session from the factory.

        Returns:
            AsyncSession instance.

        Usage:
            async with await repo.get_session() as session:
                # Use session
        """
        return self._session_factory()
