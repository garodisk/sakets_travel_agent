# TripMate AI

Personal multi-agent travel planner. You describe a trip in natural language; the graph fetches live flights, searches hotels, drafts an itinerary, then returns a formatted plan.

## How it works

LangGraph runs four agents in sequence. Conversation state is checkpointed in PostgreSQL so a `thread_id` can resume later.

```
user query
    → flight_agent     AviationStack live flights (route parsed from the query)
    → hotel_agent      Tavily web search for hotels
    → itinerary_agent  OpenRouter LLM (openai/gpt-5-mini)
    → final_agent      same LLM; sections: summary, flights, hotels, days, budget, recs
```

State (`TravelState` in `backend.py`):

- `messages`, `user_query`
- `flight_results`, `hotel_results`, `itinerary`
- `llm_calls`

`run_travel_agent(user_input, thread_id=None)` is the entry point. It returns the final answer plus intermediate fields.

## Project layout

| Path | Role |
|------|------|
| `backend.py` | Graph, Postgres checkpointer, `run_travel_agent` |
| `tools/flight_tool.py` | Parse origin/destination (city, country, IATA) and call AviationStack |
| `tools/tavily_tool.py` | Hotel-oriented Tavily search |
| `test.py` | CLI smoke test |
| `templates/`, `static/` | TripMate web UI (expects FastAPI `/api/travel`) |
| `app.py` | Intended FastAPI app — currently empty |

The UI posts JSON `{ "message", "thread_id" }` to `/api/travel` and expects `{ "success", "thread_id", "answer" }`. Until `app.py` wires that up, use `test.py` or call `run_travel_agent` from Python.

## Setup

Python 3.12+ recommended.

```powershell
cd "c:\Users\saket\projects\Saket's Tripmate"
uv venv --python 3.12
.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

Create a `.env` in the project root (do not commit it):

```env
OPENROUTER_API_KEY=
TAVILY_API_KEY=
AVIATIONSTACK_API_KEY=
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME

# Optional. Used when the query only names a destination (default: ORD).
DEFAULT_ORIGIN_IATA=ORD
```

`DATABASE_URL` should be a Postgres connection string that LangGraph can reach (for example Render’s **external** URL). `backend.py` appends `sslmode=require` if it is missing.

Optional: Groq is still listed in `requirements.txt` but the graph currently uses OpenRouter, not Groq.

## Run

```powershell
python test.py
```

That invokes:

```text
Plan a 7 days trip to MCI from Chicago on September 3 2026
```

Change the prompt in `test.py`, or:

```python
from backend import run_travel_agent

result = run_travel_agent("Plan a 5 days Dubai trip from Chicago.")
print(result["answer"])
print(result["thread_id"])
```

Flight tool only:

```powershell
python tools/flight_tool.py
```

## Flight parsing notes

AviationStack returns **live/status** flights, not ticket fares. The final LLM is instructed to say so when prices are missing.

Route examples the parser understands:

- `from Chicago to Kansas City` / IATA `ORD` `MCI`
- destination only (`Japan trip`) → origin `DEFAULT_ORIGIN_IATA`
- `all country flight info` → unfiltered live sample

If no flights match, the tool says so and points at a pricing API (e.g. Amadeus) for fares.

## Dependencies

- **LangGraph** + **langgraph-checkpoint-postgres** — graph and memory
- **langchain-openrouter** — itinerary and final write-up
- **AviationStack** — live flights
- **Tavily** — hotel search
- **FastAPI / Uvicorn / Jinja2** — for the UI once `app.py` is implemented
