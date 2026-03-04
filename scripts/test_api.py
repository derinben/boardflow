"""Quick test script for the recommendations API.

Usage:
    python scripts/test_api.py
    python scripts/test_api.py "I like Catan and want something with trading"
"""

import asyncio
import sys

import httpx
from rich.console import Console
from rich.table import Table

console = Console()


async def test_health(base_url: str = "http://localhost:8000"):
    """Test the health endpoint."""
    console.print("\n[bold cyan]Testing health endpoint...[/bold cyan]")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{base_url}/api/health", timeout=5.0)
            response.raise_for_status()
            data = response.json()

            console.print(f"[green]✓[/green] Status: {data['status']}")
            console.print(f"[green]✓[/green] Database: {data['database']}")
            console.print(f"[green]✓[/green] LLM: {data['llm']}")
            return True
        except httpx.HTTPError as e:
            console.print(f"[red]✗[/red] Health check failed: {e}")
            return False


async def test_recommendations(
    query: str,
    base_url: str = "http://localhost:8000",
    top_n: int = 5,
):
    """Test the recommendations endpoint."""
    console.print(f"\n[bold cyan]Testing recommendations endpoint...[/bold cyan]")
    console.print(f"Query: [italic]{query}[/italic]\n")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{base_url}/api/recommendations",
                json={
                    "query": query,
                    "top_n": top_n,
                    "year_min": 2015,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            console.print(f"[green]✓[/green] Received {data['count']} recommendations\n")

            # Display results in table
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("#", width=3)
            table.add_column("Game", width=30)
            table.add_column("Score", width=8)
            table.add_column("Rating", width=8)
            table.add_column("Complexity", width=10)

            for i, rec in enumerate(data["recommendations"], 1):
                table.add_row(
                    str(i),
                    rec["name"],
                    f"{rec['score']:.3f}",
                    f"{rec['rating']:.1f}" if rec["rating"] else "N/A",
                    f"{rec['complexity']:.1f}" if rec["complexity"] else "N/A",
                )

            console.print(table)

            # Show detailed explanation for top recommendation
            if data["recommendations"]:
                top = data["recommendations"][0]
                console.print(f"\n[bold]Top Recommendation:[/bold] {top['name']}")
                console.print(f"[dim]{top['explanation']}[/dim]")
                console.print(f"\nMechanics: {', '.join(top['mechanics'][:5])}")
                console.print(f"Categories: {', '.join(top['categories'][:3])}")

            return True
        except httpx.HTTPError as e:
            console.print(f"[red]✗[/red] Recommendations failed: {e}")
            if hasattr(e, "response") and e.response is not None:
                console.print(f"Response: {e.response.text}")
            return False


async def main():
    """Run API tests."""
    base_url = "http://localhost:8000"

    # Get query from CLI or use default
    query = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "I like Catan and 7 Wonders, want something with trading"
    )

    console.print("[bold]BoardFlow API Test[/bold]")
    console.print(f"Server: {base_url}\n")

    # Test health
    health_ok = await test_health(base_url)
    if not health_ok:
        console.print("\n[red]Health check failed. Is the server running?[/red]")
        console.print("Start with: make api-dev")
        sys.exit(1)

    # Test recommendations
    rec_ok = await test_recommendations(query, base_url, top_n=5)
    if not rec_ok:
        console.print("\n[red]Recommendations test failed[/red]")
        sys.exit(1)

    console.print("\n[green bold]✓ All tests passed![/green bold]")


if __name__ == "__main__":
    asyncio.run(main())
