
import json
import time
import uuid

from app.agents.planner import run_planner
from app.agents.researcher import run_researcher
from app.agents.writer import run_writer

from app.graph.build_graph import build_graph


def main():
    question = (
        "What are the main cybersecurity risks "
        "of AI in healthcare?"
    )

    graph = build_graph(
        planner_fn=run_planner,
        researcher_fn=run_researcher,
        writer_fn=run_writer,
    )

    initial_state = {
        "run_id": str(uuid.uuid4()),
        "question": question,
        "started_at": time.time(),
    }

    print("Starting research workflow...")

    result = graph.invoke(
        initial_state,
        config={"recursion_limit": 20},
    )

    print("\nFINAL STATUS:")
    print(result["status"])

    if "report" in result:
        print("\nFINAL REPORT:")
        print(
            json.dumps(
                result["report"],
                indent=2,
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
