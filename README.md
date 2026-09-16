# Multi-Agent Research Assistant

Supervisor/worker agent system (Planner -> Researcher -> Writer) with durable
Redis state, enforced budgets, source-tracked findings, and step-level tracing.

## Run locally

```bash
cp .env.example .env   # fill in GROQ_API_KEY (free at console.groq.com) and TAVILY_API_KEY
docker compose up -d redis
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

## Try it

```bash
curl -X POST localhost:8000/research -H "Content-Type: application/json" \
  -d '{"question": "Environmental impacts of lithium mining for EV batteries"}'
# -> {"run_id": "..."}

curl localhost:8000/research/<run_id>
curl localhost:8000/research/<run_id>/trace
```

## Architecture

See `docs/architecture.md`.
