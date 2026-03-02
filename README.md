# PROJECT_NAME

Brief description of what this project does.

## Architecture

```
API → ingestion/ → Postgres → models/ → serving/
```

## Local Setup

1. Copy env file and fill in values:
   ```bash
   cp .env.example .env
   ```

2. Start Postgres:
   ```bash
   docker compose up -d
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run migrations:
   ```bash
   alembic upgrade head
   ```

## Usage

```bash
# Run ingestion
python -m ingestion.client
```

## Running Tests

```bash
pytest
```

## Schema Changes

When the schema feels stable, cut a migration:
```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```
