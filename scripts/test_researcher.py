
from app.agents.researcher import run_researcher
from app.schemas.plan import SubQuestion


def main():
    question = SubQuestion(
        id="Q1",
        question="What are the main AI cybersecurity threats?"
    )

    result = run_researcher(question)

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
