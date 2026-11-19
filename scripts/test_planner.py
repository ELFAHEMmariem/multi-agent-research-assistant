
from app.agents.planner import run_planner


def main():
    question = (
        "What are the main cybersecurity risks "
        "of AI in healthcare?"
    )

    plan = run_planner(question)

    print(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
