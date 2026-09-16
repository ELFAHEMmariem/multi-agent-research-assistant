from fastapi import FastAPI
from app.api import routes_research, routes_trace, streaming

app = FastAPI(title="Multi-Agent Research Assistant")

app.include_router(routes_research.router, tags=["research"])
app.include_router(routes_trace.router, tags=["trace"])
app.include_router(streaming.router, tags=["stream"])


@app.get("/health")
async def health():
    return {"status": "ok"}
