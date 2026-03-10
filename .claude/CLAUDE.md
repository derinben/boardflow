# Project Rules

## Logging
- ALWAYS use `loguru` for all logging. Never use Python's built-in `logging` module or `print` statements for debugging.
- Import pattern: `from loguru import logger`

## Documentation
- Extra docs go ONLY under /docs
- ALWAYS ask user for confirmation before creating or modifying any file under /docs

## General Behavior
- Keep the code base clean, readable, modular, and well-documented
- At the end of a session, figure out whether an existing doc needs to be updated and if there is too much of divergent changes, create a new file.