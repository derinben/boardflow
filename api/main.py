"""FastAPI application entry point.

Run with:
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

Or via make:
    make api-dev
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

from api.app import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
