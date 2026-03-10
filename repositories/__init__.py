"""Repository layer for database access.

Provides clean separation between business logic and data access.
"""

from .game_repository import GameRepository

__all__ = ["GameRepository"]
