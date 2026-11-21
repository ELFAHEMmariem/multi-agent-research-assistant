
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import TypedDict

from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from app.persistence.checkpoint import (
    redis_checkpointer,
)

from app.persistence.redis_client import (
    get_redis_client,
)


# =====================================================
# CONFIGURATION
# =====================================================

LOG_DIR = Path("logs") / "crash_recovery"
LOG_DIR.mkdir(parents=True, exist_ok=True)

START_TIMEOUT = 30
RESUME_TIMEOUT = 60


# =====================================================
# STATE FOR THE TEST GRAPH
# =====================================================

class TestState(TypedDict, total=False):
    question: str
    plan: list[str]
    findings: list[str]
    report: str
    status: str


# =====================================================
# BUILD TEST GRAPH
# =====================================================

def build_test_graph(run_id, client, checkpointer, mode):

    def planner(state: TestState):

        calls = client.incr(
            f"crash:{run_id}:planner_calls"
        )

        print(
            f"[PLANNER] Execution: {calls}",
            flush=True,
        )

        return {
            "plan": ["Q1"],
            "status": "planned",
        }

    def researcher(state: TestState):

        calls = client.incr(
            f"crash:{run_id}:researcher_calls"
        )

        print(
            f"[RESEARCHER] Execution: {calls}",
            flush=True,
        )

        if mode == "first" and calls == 1:

            client.set(
                f"crash:{run_id}:started",
                "yes",
            )

            print(
                "[RESEARCHER] Waiting for crash...",
                flush=True,
            )

            # The controller kills this process.
            time.sleep(60)

        return {
            "findings": [
                "AI security requires access controls."
            ],
            "status": "researched",
        }

    def writer(state: TestState):

        calls = client.incr(
            f"crash:{run_id}:writer_calls"
        )

        print(
            f"[WRITER] Execution: {calls}",
            flush=True,
        )

        findings = state.get("findings", [])

        if not findings:
            raise RuntimeError(
                "Writer received no findings"
            )

        return {
            "report": (
                "Research completed: "
                + "; ".join(findings)
            ),
            "status": "completed",
        }

    builder = StateGraph(TestState)

    builder.add_node("planner", planner)
    builder.add_node("researcher", researcher)
    builder.add_node("writer", writer)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "researcher")
    builder.add_edge("researcher", "writer")
    builder.add_edge("writer", END)

    return builder.compile(
        checkpointer=checkpointer,
    )


# =====================================================
# WORKER PROCESS
# =====================================================

def run_worker(mode: str, run_id: str):

    client = get_redis_client()

    config = {
        "configurable": {
            "thread_id": run_id,
        }
    }

    try:
        print(
            f"[WORKER] Mode: {mode}",
            flush=True,
        )

        with redis_checkpointer() as checkpointer:

            graph = build_test_graph(
                run_id=run_id,
                client=client,
                checkpointer=checkpointer,
                mode=mode,
            )

            if mode == "first":

                print(
                    "[WORKER] Running Planner...",
                    flush=True,
                )

                # Stop before Researcher and save
                # an explicit checkpoint.
                graph.invoke(
                    {
                        "question": "AI cybersecurity risks",
                        "status": "running",
                    },
                    config=config,
                    interrupt_before=["researcher"],
                )

                snapshot = graph.get_state(config)

                print(
                    "[CHECKPOINT] Next nodes:",
                    snapshot.next,
                    flush=True,
                )

                if "researcher" not in snapshot.next:
                    raise RuntimeError(
                        "Checkpoint is not before Researcher"
                    )

                checkpoint_id = (
                    snapshot.config["configurable"]
                    .get("checkpoint_id")
                )

                if not checkpoint_id:
                    raise RuntimeError(
                        "No checkpoint_id available"
                    )

                # Preserve the precise checkpoint
                # that we know is safe to resume.
                client.set(
                    f"crash:{run_id}:safe_checkpoint",
                    checkpoint_id,
                )

                print(
                    "[CHECKPOINT] Saved:",
                    checkpoint_id,
                    flush=True,
                )

                print(
                    "[WORKER] Starting Researcher...",
                    flush=True,
                )

                # This execution will be killed
                # while Researcher is running.
                graph.invoke(
                    None,
                    config=config,
                )

            elif mode == "resume":

                checkpoint_id = client.get(
                    f"crash:{run_id}:safe_checkpoint"
                )

                if not checkpoint_id:
                    raise RuntimeError(
                        "Saved checkpoint not found"
                    )

                # Resume from the known checkpoint,
                # not from an ambiguous latest state.
                resume_config = {
                    "configurable": {
                        "thread_id": run_id,
                        "checkpoint_id": checkpoint_id,
                    }
                }

                print(
                    "[WORKER] Resuming checkpoint:",
                    checkpoint_id,
                    flush=True,
                )

                snapshot = graph.get_state(
                    resume_config
                )

                print(
                    "[CHECKPOINT] Next nodes:",
                    snapshot.next,
                    flush=True,
                )

                if "researcher" not in snapshot.next:
                    raise RuntimeError(
                        "Saved checkpoint cannot resume "
                        "Researcher"
                    )

                result = graph.invoke(
                    None,
                    config=resume_config,
                )

                print(
                    "FINAL STATUS:",
                    result.get("status"),
                    flush=True,
                )

                if result.get("status") != "completed":
                    raise AssertionError(
                        "Workflow did not complete"
                    )

                if not result.get("report"):
                    raise AssertionError(
                        "Final report is missing"
                    )

            else:
                raise ValueError(
                    f"Unknown worker mode: {mode}"
                )

    finally:
        client.close()


# =====================================================
# CRASH TEST CONTROLLER
# =====================================================

def run_crash_test():

    run_id = f"crash-test-{uuid.uuid4()}"

    log_path = LOG_DIR / f"{run_id}.log"

    print("=" * 55)
    print("LANGGRAPH REDIS CRASH RECOVERY TEST")
    print("=" * 55)

    print("Run ID:", run_id)
    print("Log file:", log_path.resolve())

    client = get_redis_client()
    process = None

    try:
        client.ping()

        first_command = [
            sys.executable,
            "-u",
            "-m",
            "scripts.demo_real_crash",
            "worker",
            "first",
            run_id,
        ]

        # ---------------------------------------------
        # 1. Start first worker
        # ---------------------------------------------

        print("\n[1] Starting first Worker...")

        with log_path.open(
            "w",
            encoding="utf-8",
        ) as log_file:

            process = subprocess.Popen(
                first_command,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )

            print(
                "[2] Waiting for Researcher..."
            )

            deadline = (
                time.monotonic() + START_TIMEOUT
            )

            while time.monotonic() < deadline:

                started = client.get(
                    f"crash:{run_id}:started"
                )

                if started == "yes":
                    break

                if process.poll() is not None:

                    raise RuntimeError(
                        "First Worker exited unexpectedly"
                    )

                time.sleep(0.1)

            else:
                raise TimeoutError(
                    "Researcher did not start in time"
                )

            # -----------------------------------------
            # 2. Kill worker during Researcher
            # -----------------------------------------

            print("[3] Researcher started.")
            print("[4] Killing first Worker...")

            process.kill()
            process.wait(timeout=10)

        # Read logs after file has been closed.
        first_log = log_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        print("\nFIRST WORKER LOG:")
        print(first_log)

        if "[CHECKPOINT] Saved:" not in first_log:
            raise AssertionError(
                "Safe checkpoint was not saved"
            )

        # ---------------------------------------------
        # 3. Resume with a second worker
        # ---------------------------------------------

        print("[5] Starting second Worker...")

        resume_command = [
            sys.executable,
            "-u",
            "-m",
            "scripts.demo_real_crash",
            "worker",
            "resume",
            run_id,
        ]

        resumed = subprocess.run(
            resume_command,
            capture_output=True,
            text=True,
            timeout=RESUME_TIMEOUT,
        )

        print("\nSECOND WORKER OUTPUT:")
        print(resumed.stdout)

        if resumed.stderr:
            print("\nSECOND WORKER ERROR:")
            print(resumed.stderr)

        if resumed.returncode != 0:
            raise RuntimeError(
                "Second Worker failed with "
                f"exit code {resumed.returncode}"
            )

        # ---------------------------------------------
        # 4. Read execution counters
        # ---------------------------------------------

        planner_calls = int(
            client.get(
                f"crash:{run_id}:planner_calls"
            ) or 0
        )

        researcher_calls = int(
            client.get(
                f"crash:{run_id}:researcher_calls"
            ) or 0
        )

        writer_calls = int(
            client.get(
                f"crash:{run_id}:writer_calls"
            ) or 0
        )

        print("\n" + "=" * 55)
        print("CRASH RECOVERY RESULTS")
        print("=" * 55)

        print("Planner calls:", planner_calls)
        print("Researcher calls:", researcher_calls)
        print("Writer calls:", writer_calls)

        # ---------------------------------------------
        # 5. Verify actual recovery
        # ---------------------------------------------

        assert planner_calls == 1, (
            "Planner should execute exactly once"
        )

        assert researcher_calls == 2, (
            "Researcher should execute twice"
        )

        assert writer_calls == 1, (
            "Writer should execute exactly once"
        )

        assert (
            "FINAL STATUS: completed"
            in resumed.stdout
        ), "Missing successful completion"

        print("\nCRASH RECOVERY TEST PASSED")

    except Exception as exc:

        print("\nCRASH RECOVERY TEST FAILED")
        print("Error:", str(exc))

        if log_path.exists():
            print("\nFIRST WORKER LOG:")
            print(
                log_path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            )

        raise

    finally:

        if process is not None:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)

        client.close()


# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    if (
        len(sys.argv) == 4
        and sys.argv[1] == "worker"
    ):
        run_worker(
            mode=sys.argv[2],
            run_id=sys.argv[3],
        )

    else:
        run_crash_test()
