from backend import run_travel_agent
from rich.console import Console
from rich.markdown import Markdown

result = run_travel_agent(
    "Plan a 7 days trip to MCI from Chicago on September 3 2026"
)

console = Console()
console.print(Markdown(result["answer"]))