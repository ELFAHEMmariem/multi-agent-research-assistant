"""Invoke the graph directly, no API/uvicorn, for fast iteration on prompts."""
import asyncio
import sys
from app.schemas.state import GraphState
from app.graph.build_graph import run_graph


async def main(question: str):
    state = GraphState(run_id="local-dev", original_question=question)
    final = await run_graph(state)
    print(f"status: {final.status}")
    if final.report:
        print(final.report.body)
    if final.error:
        print(f"error: {final.error}")


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "Environmental impacts of lithium mining for EV batteries"
    asyncio.run(main(q))
