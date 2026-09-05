# TripMate AI

WORK IN PROGRESS

Personal multi-agent travel planner. You describe a trip in natural language; the graph fetches live flights, searches hotels, drafts an itinerary, then returns a formatted plan in the FastAPI UI.

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

`run_travel_agent(user_input, thread_id=None)` in `backend.py` is the graph entry point. FastAPI (`app.py`) calls it from `POST /api/travel`.

## Project layout

| Path | Role |
|------|------|
| `app.py` | FastAPI server: UI, `/api/travel`, health check |
| `backend.py` | Graph, Postgres checkpointer, `run_travel_agent` |
| `tools/flight_tool.py` | Parse origin/destination (city, country, IATA) and call AviationStack |
| `tools/tavily_tool.py` | Hotel-oriented Tavily search |
| `templates/index.html` | TripMate web UI |
| `static/` | CSS and frontend JS |
| `test.py` | CLI smoke test (bypasses FastAPI) |
| `Dockerfile` | Production image: Python 3.11, Uvicorn on port 8000 |
| `.dockerignore` | Excludes local virtualenvs from the image |

## FastAPI

`app.py` serves the UI and JSON API.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Jinja2 `index.html` (TripMate planner) |
| `POST` | `/api/travel` | Run the travel graph |
| `GET` | `/health` | `{ "status": "ok" }` |
| `GET` | `/static/...` | CSS / JS |

Request body for `/api/travel`:

```json
{
  "message": "Plan a 5 days Dubai trip from Chicago.",
  "thread_id": null
}
```

`thread_id` is optional. The UI stores it in `localStorage` so later requests continue the same checkpointed thread.

Success response:

```json
{
  "success": true,
  "thread_id": "user_...",
  "answer": "...markdown plan...",
  "flight_results": "...",
  "hotel_results": "...",
  "itinerary": "...",
  "llm_calls": 4
}
```

Empty messages return `400`. Unhandled errors return `500` with `{ "success": false, "error": "..." }`.

The page also supports copy-to-clipboard and PDF download of the rendered plan.

## Setup

Python 3.12+ locally (the Docker image uses **3.11-slim**).

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

Groq is still listed in `requirements.txt` but the graph currently uses OpenRouter, not Groq.

## Run locally

Web app (reload on `127.0.0.1:8000`):

```powershell
python app.py
```

Equivalent:

```powershell
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health).

CLI without the UI:

```powershell
python test.py
```

That invokes:

```text
Plan a 7 days trip to MCI from Chicago on September 3 2026
```

Or from Python:

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

## Docker

The image installs `requirements.txt`, copies the app, and starts Uvicorn on `0.0.0.0:8000`.

Build:

```powershell
docker build -t tripmate-ai .
```

Run (pass secrets from `.env`; do not bake keys into the image):

```powershell
docker run --rm -p 8000:8000 --env-file .env tripmate-ai
```

Then open [http://localhost:8000](http://localhost:8000).

`.dockerignore` skips `.venv` / `venv` so local environments are not copied into the image.

## Flight parsing notes

AviationStack returns **live/status** flights, not ticket fares. The final LLM is instructed to say so when prices are missing.

Route examples the parser understands:

- `from Chicago to Kansas City` / IATA `ORD` `MCI`
- destination only (`Japan trip`) → origin `DEFAULT_ORIGIN_IATA`
- `all country flight info` → unfiltered live sample

If no flights match, the tool says so and points at a pricing API (e.g. Amadeus) for fares.

## Dependencies

- **FastAPI / Uvicorn / Jinja2** — web UI and `/api/travel`
- **LangGraph** + **langgraph-checkpoint-postgres** — graph and memory
- **langchain-openrouter** — itinerary and final write-up
- **AviationStack** — live flights
- **Tavily** — hotel search
