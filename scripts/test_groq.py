
from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import get_llm


def main():
    llm = get_llm()

    messages = [
        SystemMessage(
            content="You are a concise research assistant."
        ),
        HumanMessage(
            content="Explain what a multi-agent AI system is in two sentences."
        ),
    ]

    response = llm.invoke(messages)

    print("\nMODEL RESPONSE:")
    print(response.content)

    print("\nTOKEN USAGE:")
    print(response.usage_metadata)


if __name__ == "__main__":
    main()
