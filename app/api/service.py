
import json
import logging
import time
from datetime import datetime, timezone

from app.agents.planner import run_planner
from app.agents.researcher import run_researcher
from app.agents.writer import run_writer

from app.graph.build_graph import build_graph

from app.persistence.checkpoint import (
    redis_checkpointer,
)

from app.persistence.redis_client import (
    get_redis_client,
)


logger = logging.getLogger(__name__)

RUN_TTL = 7 * 24 * 3600


# ==================================================
# 1. REDIS KEYS
# ==================================================

def run_key(run_id: str) -> str:
    return f"research:api:run:{run_id}"


def events_key(run_id: str) -> str:
    return f"research:api:events:{run_id}"


# ==================================================
# 2. SAVE RESEARCH STATUS
# ==================================================

def save_run(
    run_id: str,
    question: str,
    status: str,
    error: str = "",
    report: dict | None = None,
) -> None:

    client = get_redis_client()

    try:
        data = {
            "run_id": run_id,
            "question": question,
            "status": status,
            "error": error,
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        if report is not None:

            if hasattr(report, "model_dump"):
                report = report.model_dump(
                    mode="json"
                )

            data["report"] = json.dumps(
                report,
                ensure_ascii=False,
                default=str,
            )

        with client.pipeline() as pipe:
            pipe.hset(
                run_key(run_id),
                mapping=data,
            )

            pipe.expire(
                run_key(run_id),
                RUN_TTL,
            )

            pipe.execute()

    finally:
        client.close()


# ==================================================
# 3. GET RESEARCH STATUS
# ==================================================

def get_run(run_id: str) -> dict | None:

    client = get_redis_client()

    try:
        data = client.hgetall(
            run_key(run_id)
        )

        if not data:
            return None

        # Support Redis clients returning bytes.
        data = {
            (
                key.decode("utf-8")
                if isinstance(key, bytes)
                else key
            ): (
                value.decode("utf-8")
                if isinstance(value, bytes)
                else value
            )
            for key, value in data.items()
        }

        if "report" in data:
            data["report"] = json.loads(
                data["report"]
            )

        return data

    finally:
        client.close()


# ==================================================
# 4. SAVE SSE EVENT
# ==================================================

def add_event(
    run_id: str,
    event_type: str,
    message: str,
    node: str | None = None,
) -> None:

    client = get_redis_client()

    try:
        event = {
            "type": event_type,
            "message": message,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        if node is not None:
            event["node"] = node

        key = events_key(run_id)

        with client.pipeline() as pipe:

            pipe.rpush(
                key,
                json.dumps(
                    event,
                    ensure_ascii=False,
                ),
            )

            pipe.expire(
                key,
                RUN_TTL,
            )

            pipe.execute()

    finally:
        client.close()


# ==================================================
# 5. GET SSE EVENTS
# ==================================================

def get_events(
    run_id: str,
    start_index: int = 0,
) -> list[dict]:

    client = get_redis_client()

    try:
        raw_events = client.lrange(
            events_key(run_id),
            start_index,
            -1,
        )

        return [
            json.loads(item)
            for item in raw_events
        ]

    finally:
        client.close()


# ==================================================
# 6. BUILD LANGGRAPH
# ==================================================

def create_research_graph(checkpointer):

    return build_graph(planner_fn=run_planner, researcher_fn=run_researcher, writer_fn=run_writer, checkpointer=checkpointer, use_llm_review=True)


def graph_config(run_id: str) -> dict:

    return {
        "configurable": {
            "thread_id": run_id,
        },
        "recursion_limit": 30,
    }


# ==================================================
# 7. RECORD NODE EVENTS
# ==================================================

def record_graph_updates(
    run_id: str,
    chunk: dict,
) -> None:
    """
    Receives LangGraph stream updates.

    Saves one event for every completed node.
    """

    if not isinstance(chunk, dict):
        return

    for node_name, update in chunk.items():

        if node_name == "__interrupt__":
            add_event(
                run_id,
                "interrupted",
                "Graph execution interrupted",
            )
            continue

        add_event(
            run_id,
            "node_completed",
            f"Node {node_name} completed",
            node=str(node_name),
        )


# ==================================================
# 8. EXECUTE RESEARCH WITH STREAMING
# ==================================================

def execute_research(
    run_id: str,
    question: str,
) -> None:

    config = graph_config(run_id)

    save_run(
        run_id,
        question,
        "running",
    )

    add_event(
        run_id,
        "running",
        "Research workflow started",
    )

    try:
        with redis_checkpointer() as checkpointer:

            graph = create_research_graph(
                checkpointer
            )

            snapshot = graph.get_state(config)

            # --------------------------------------
            # A. NEW RUN OR RESUMED RUN
            # --------------------------------------

            if snapshot.values:

                if snapshot.next:
                    graph_input = None

                elif (
                    snapshot.values.get("status")
                    == "completed"
                ):

                    report = snapshot.values.get(
                        "report"
                    )

                    if report is None:
                        raise RuntimeError(
                            "Completed run has no report"
                        )

                    save_run(
                        run_id,
                        question,
                        "completed",
                        report=report,
                    )

                    add_event(
                        run_id,
                        "completed",
                        "Existing completed run loaded",
                    )

                    return

                else:
                    raise RuntimeError(
                        "Existing run has no pending "
                        "nodes and is not completed"
                    )

            else:
                graph_input = {
                    "run_id": run_id,
                    "question": question,
                    "started_at": time.time(),
                }

            # --------------------------------------
            # B. STREAM LANGGRAPH NODE UPDATES
            # --------------------------------------

            for chunk in graph.stream(
                graph_input,
                config=config,
                stream_mode="updates",
            ):

                record_graph_updates(
                    run_id,
                    chunk,
                )

            # --------------------------------------
            # C. READ FINAL CHECKPOINT
            # --------------------------------------

            final_snapshot = graph.get_state(
                config
            )

            final_state = final_snapshot.values

            final_status = final_state.get(
                "status",
                "stopped",
            )

            # --------------------------------------
            # D. HANDLE COMPLETED RESEARCH
            # --------------------------------------

            if final_status == "completed":

                report = final_state.get(
                    "report"
                )

                if report is None:
                    raise RuntimeError(
                        "Completed run has no report"
                    )

                save_run(
                    run_id,
                    question,
                    "completed",
                    report=report,
                )

                add_event(
                    run_id,
                    "completed",
                    "Research report generated",
                )

            # --------------------------------------
            # E. HANDLE INTERRUPTED RESEARCH
            # --------------------------------------

            elif final_snapshot.next:

                save_run(
                    run_id,
                    question,
                    "interrupted",
                    error=(
                        "Workflow has pending nodes"
                    ),
                )

                add_event(
                    run_id,
                    "interrupted",
                    "Research has pending nodes",
                )

            # --------------------------------------
            # F. HANDLE STOPPED RESEARCH
            # --------------------------------------

            else:

                save_run(
                    run_id,
                    question,
                    "stopped",
                    error=(
                        final_state.get("stop_reason")
                        or "Workflow did not complete"
                    ),
                )

                add_event(
                    run_id,
                    "stopped",
                    "Research workflow stopped",
                )

    # ------------------------------------------
    # G. HANDLE ERRORS
    # ------------------------------------------

    except Exception as exc:

        logger.exception(
            "Research execution failed: %s",
            run_id,
        )

        save_run(
            run_id,
            question,
            "failed",
            error=type(exc).__name__,
        )

        add_event(
            run_id,
            "failed",
            "Research workflow failed",
        )


# ==================================================
# 9. RETRIEVE CITATIONS
# ==================================================

def get_research_citations(
    run_id: str,
) -> dict:

    from app.graph.citation_validator import (
        validate_citations,
    )

    run = get_run(run_id)

    if run is None:
        raise KeyError(
            "Research run not found"
        )

    if run.get("status") != "completed":
        raise ValueError(
            "Research is not completed"
        )

    config = graph_config(run_id)

    with redis_checkpointer() as checkpointer:

        graph = create_research_graph(
            checkpointer
        )

        snapshot = graph.get_state(config)

        state = snapshot.values

        report = state.get("report")

        findings = state.get(
            "findings",
            [],
        )

        if report is None:
            raise ValueError(
                "Report not found in checkpoint"
            )

        result = validate_citations(
            report=report,
            findings=findings,
        )

        return {
            "run_id": run_id,
            **result,
        }
