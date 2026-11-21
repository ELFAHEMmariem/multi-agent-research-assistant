
import json
import sys
import time
import uuid

from app.agents.planner import run_planner
from app.agents.researcher import run_researcher
from app.agents.writer import run_writer

from app.graph.build_graph import build_graph

from app.graph.token_budget import (
    check_token_budget,
    TokenBudgetExceeded,
)

from app.persistence.checkpoint import (
    redis_checkpointer,
)

from app.persistence.token_tracker import (
    GroqTokenTracker,
    get_token_usage,
)


def main():

    # 1. Choose run ID
    if len(sys.argv) >= 2:
        run_id = sys.argv[1]
    else:
        run_id = str(uuid.uuid4())

    print("=" * 55)
    print("MULTI-AGENT RESEARCH ASSISTANT")
    print("=" * 55)
    print("Run ID:", run_id)

    # 2. Define LangGraph configuration
    config = {
        "configurable": {
            "thread_id": run_id,
        },
        "recursion_limit": 30,
        "callbacks": [
            GroqTokenTracker(run_id)
        ],
    }

    # 3. Wrap LLM agents with budget checks
    def tracked_planner(question):
        check_token_budget(run_id)
        return run_planner(question)

    def tracked_writer(question, findings):
        check_token_budget(run_id)
        return run_writer(
            question,
            findings,
        )

    # 4. Open Redis and compile graph
    with redis_checkpointer() as checkpointer:

        graph = build_graph(
            planner_fn=tracked_planner,
            researcher_fn=run_researcher,
            writer_fn=tracked_writer,
            checkpointer=checkpointer,
            use_cache=True,
        )

        # 5. Inspect existing run
        snapshot = graph.get_state(config)

        if snapshot.values:

            if not snapshot.next:
                print(
                    "\nThis run is already finished."
                )
                result = snapshot.values

                print_summary(run_id, result)
                return

            print("\nResuming existing run...")
            graph_input = None

        else:
            print("\nStarting new run...")

            question = (
                "What are the main AI "
                "cybersecurity risks?"
            )

            graph_input = {
                "run_id": run_id,
                "question": question,
                "started_at": time.time(),
            }

        # 6. Execute
        try:
            result = graph.invoke(
                graph_input,
                config=config,
            )

        except TokenBudgetExceeded as exc:
            print("\nTOKEN BUDGET EXCEEDED")
            print(str(exc))
            print_token_usage(run_id)
            raise

        except Exception as exc:
            print("\nWORKFLOW FAILED")
            print("Error type:", type(exc).__name__)
            print("Error:", str(exc))

            print_token_usage(run_id)

            latest = graph.get_state(config)

            if latest.values:
                print(
                    "Next nodes:",
                    latest.next,
                )
                print(
                    "You can retry with run ID:",
                    run_id,
                )

            raise

        # 7. Display final result
        print_summary(run_id, result)


def print_token_usage(run_id: str):
    usage = get_token_usage(run_id)

    print("\nGROQ TOKEN USAGE")
    print("-" * 30)

    print(
        "Input tokens:",
        usage["input_tokens"],
    )
    print(
        "Output tokens:",
        usage["output_tokens"],
    )
    print(
        "Total tokens:",
        usage["total_tokens"],
    )


def print_summary(run_id: str, result: dict):
    print("\n" + "=" * 55)
    print("WORKFLOW RESULT")
    print("=" * 55)

    print("Run ID:", run_id)
    print(
        "Status:",
        result.get("status", "unknown"),
    )

    print("\nFinal state:")

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

    print_token_usage(run_id)

    print("\nExecution finished.")


if __name__ == "__main__":
    main()
