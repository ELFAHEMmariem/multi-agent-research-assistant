"""Pretty-print a stored trace for debugging a bad run."""
import asyncio
import sys
from app.persistence.trace_store import get_trace


async def main(run_id: str):
    events = await get_trace(run_id)
    for i, e in enumerate(events, 1):
        print(f"[{i}] {e['node']:12s} {e['latency_ms']:5d}ms  {e['output_summary']}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
