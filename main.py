"""boardflow — BGG data ingestion and modelling platform.

Run the ingestion pipeline directly:
    python scripts/run_ingestion.py --mode info
    python scripts/run_ingestion.py --mode stats

Or via Makefile:
    make ingest-info
    make ingest-stats
"""


def main() -> None:
    # Intentionally minimal — all pipeline logic lives in scripts/.
    print("boardflow: use `python scripts/run_ingestion.py --help` to get started.")


if __name__ == "__main__":
    main()
